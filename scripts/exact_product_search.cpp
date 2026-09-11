#include <algorithm>
#include <array>
#include <chrono>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Counts = std::array<int, 26>;

struct Entry {
  int cell;
  int letter;
  int coefficient;
};

struct Option {
  int face_score;
  long long reduced_loss = 0;
  std::string word;
  int index;
  int start_row;
  Counts counts_without_new;
  std::vector<Entry> entries;
};

struct Record {
  int score;
  int face_score;
  int penalty;
  std::vector<int> selected;
};

constexpr std::array<int, 26> kLetterValues = {
    1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 1, 3, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10};
constexpr std::array<int, 26> kTileDistribution = {
    9, 2, 2, 4, 12, 2, 3, 2, 9, 1, 1, 4, 2, 6, 8, 2, 1, 6, 4, 6, 4, 2, 2, 1, 2, 1};

int blank_count_for_counts(const Counts& counts) {
  int total = 0;
  for (int i = 0; i < 26; ++i) {
    if (counts[i] > kTileDistribution[i]) total += counts[i] - kTileDistribution[i];
  }
  return total;
}

int optimistic_blank_penalty_for_counts(const Counts& counts) {
  int total = 0;
  for (int i = 0; i < 26; ++i) {
    if (counts[i] > kTileDistribution[i]) {
      total += (counts[i] - kTileDistribution[i]) * kLetterValues[i];
    }
  }
  return total;
}

Counts add_counts(const Counts& left, const Counts& right) {
  Counts result;
  for (int i = 0; i < 26; ++i) result[i] = left[i] + right[i];
  return result;
}

int score_after_best_blanks(
    int face_score,
    const std::vector<Entry>& main_entries,
    const std::vector<std::vector<Option>>& slots,
    const std::vector<int>& selected,
    int* penalty_out) {
  std::array<int, 225> letters;
  std::array<int, 225> coefficients;
  letters.fill(-1);
  coefficients.fill(0);

  auto add_entry = [&](const Entry& entry) {
    int existing = letters[entry.cell];
    if (existing != -1 && existing != entry.letter) {
      throw std::runtime_error("conflicting letters on one cell");
    }
    letters[entry.cell] = entry.letter;
    coefficients[entry.cell] += entry.coefficient;
  };

  for (const Entry& entry : main_entries) add_entry(entry);
  for (std::size_t slot = 0; slot < selected.size(); ++slot) {
    int option_index = selected[slot];
    if (option_index < 0) continue;
    for (const Entry& entry : slots[slot][option_index].entries) add_entry(entry);
  }

  std::array<int, 26> counts;
  counts.fill(0);
  std::array<std::vector<int>, 26> coeffs_by_letter;
  for (int cell = 0; cell < 225; ++cell) {
    int letter = letters[cell];
    if (letter < 0) continue;
    counts[letter] += 1;
    coeffs_by_letter[letter].push_back(coefficients[cell]);
  }

  int blank_count = 0;
  int penalty = 0;
  for (int letter = 0; letter < 26; ++letter) {
    int over = counts[letter] - kTileDistribution[letter];
    if (over <= 0) continue;
    blank_count += over;
    if (blank_count > 2) {
      *penalty_out = penalty;
      return -1;
    }
    auto& coeffs = coeffs_by_letter[letter];
    std::sort(coeffs.begin(), coeffs.end());
    for (int i = 0; i < over; ++i) penalty += kLetterValues[letter] * coeffs[i];
  }
  *penalty_out = penalty;
  return face_score - penalty;
}

struct Search {
  int best;
  bool retain_all = false;
  long long price_scale = 1;
  long long resource_upper = 0;
  bool use_prices = false;
  int main_face;
  int mandatory_main_penalty = 0;
  Counts main_counts;
  std::vector<Entry> main_entries;
  std::vector<std::vector<Option>> slots;
  std::vector<int> ordered_slots;
  std::vector<int> suffix_top;
  std::vector<int> selected;
  std::vector<Record> records;
  long long leaves = 0;
  long long nodes = 0;
  int keep_records = 25;
  std::chrono::steady_clock::time_point started;
  std::chrono::steady_clock::time_point last_report;

  void dfs(int offset, int face_score, const Counts& counts, long long loss = 0) {
    nodes += 1;
    if (use_prices && resource_upper - loss < price_scale * best) return;
    if ((nodes & ((1 << 24) - 1)) == 0) {
      auto now = std::chrono::steady_clock::now();
      double elapsed = std::chrono::duration<double>(now - started).count();
      if (std::chrono::duration<double>(now - last_report).count() >= 10.0) {
        std::cerr << "nodes=" << nodes << " leaves=" << leaves << " best=" << best
                  << " elapsed=" << elapsed << "s\n";
        last_report = now;
      }
    }
    if (offset == static_cast<int>(ordered_slots.size())) {
      leaves += 1;
      int penalty = 0;
      int score = score_after_best_blanks(face_score, main_entries, slots, selected, &penalty);
      if (score < best) return;
      if (score > best && !retain_all) {
        best = score;
        records.clear();
        std::cout << "new best " << best << " face " << face_score << " penalty " << penalty
                  << " selection";
        for (int option_index : selected) std::cout << ' ' << option_index;
        std::cout << "\n";
      }
      records.push_back({score, face_score, penalty, selected});
      std::sort(records.begin(), records.end(), [](const Record& a, const Record& b) {
        return a.score > b.score;
      });
      if (!retain_all && static_cast<int>(records.size()) > keep_records) records.resize(keep_records);
      return;
    }

    int slot = ordered_slots[offset];
    int remaining_after_slot = suffix_top[offset + 1];
    const auto& options = slots[slot];
    for (int option_index = 0; option_index < static_cast<int>(options.size()); ++option_index) {
      const Option& option = options[option_index];
      int next_face = face_score + option.face_score;
      // Blanks forced inside the main word cannot be moved to future support.
      if (next_face + remaining_after_slot - mandatory_main_penalty < best) break;
      Counts next_counts = add_counts(counts, option.counts_without_new);
      if (blank_count_for_counts(next_counts) > 2) continue;
      if (next_face + remaining_after_slot - optimistic_blank_penalty_for_counts(next_counts) < best) {
        continue;
      }
      selected[slot] = option.word == "." ? -1 : option_index;
      dfs(offset + 1, next_face, next_counts, loss + option.reduced_loss);
      selected[slot] = -1;
    }
  }
};

Counts read_counts(std::istream& in) {
  Counts counts;
  for (int i = 0; i < 26; ++i) in >> counts[i];
  return counts;
}

std::vector<Entry> read_entries(std::istream& in, int n) {
  std::vector<Entry> entries;
  entries.reserve(n);
  for (int i = 0; i < n; ++i) {
    Entry entry;
    in >> entry.cell >> entry.letter >> entry.coefficient;
    entries.push_back(entry);
  }
  return entries;
}

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: exact_product_search INSTANCE [keep_records]\n";
    return 2;
  }
  Search search;
  if (argc >= 3) search.keep_records = std::stoi(argv[2]);
  if (argc >= 4 && std::string(argv[3]) == "--all") search.retain_all = true;
  std::ifstream in(argv[1]);
  if (!in) {
    std::cerr << "cannot open " << argv[1] << "\n";
    return 2;
  }

  std::string tag;
  int slots_count = 0;
  in >> tag >> search.best;
  if (tag != "BEST") throw std::runtime_error("expected BEST");
  in >> tag >> slots_count;
  if (tag != "SLOTS") throw std::runtime_error("expected SLOTS");
  in >> tag >> search.main_face;
  if (tag != "MAIN_FACE") throw std::runtime_error("expected MAIN_FACE");
  std::string ignored;
  in >> tag >> ignored;
  if (tag != "MAIN_WORD") throw std::runtime_error("expected MAIN_WORD");
  std::getline(in, ignored);
  in >> tag;
  if (tag != "MAIN_INDICES") throw std::runtime_error("expected MAIN_INDICES");
  std::getline(in, ignored);
  in >> tag;
  if (tag != "MAIN_CELLS") throw std::runtime_error("expected MAIN_CELLS");
  std::getline(in, ignored);
  in >> tag;
  if (tag != "MAIN_COUNTS") throw std::runtime_error("expected MAIN_COUNTS");
  search.main_counts = read_counts(in);
  int main_entries_count = 0;
  in >> tag >> main_entries_count;
  if (tag != "MAIN_ENTRIES") throw std::runtime_error("expected MAIN_ENTRIES");
  search.main_entries = read_entries(in, main_entries_count);

  search.slots.resize(slots_count);
  for (int slot_no = 0; slot_no < slots_count; ++slot_no) {
    int slot_index = 0;
    int option_count = 0;
    in >> tag >> slot_index >> option_count;
    if (tag != "SLOT" || slot_index != slot_no) throw std::runtime_error("expected SLOT");
    auto& options = search.slots[slot_no];
    options.reserve(option_count);
    for (int option_no = 0; option_no < option_count; ++option_no) {
      Option option;
      int entry_count = 0;
      in >> tag >> option.face_score >> option.word >> option.index >> option.start_row >> entry_count;
      if (tag != "OPTION") throw std::runtime_error("expected OPTION");
      option.counts_without_new = read_counts(in);
      option.entries = read_entries(in, entry_count);
      options.push_back(std::move(option));
    }
    std::sort(options.begin(), options.end(), [](const Option& a, const Option& b) {
      return a.face_score > b.face_score;
    });
  }

  search.ordered_slots.resize(slots_count);
  std::iota(search.ordered_slots.begin(), search.ordered_slots.end(), 0);
  std::sort(search.ordered_slots.begin(), search.ordered_slots.end(), [&](int a, int b) {
    if (search.slots[a].size() != search.slots[b].size()) {
      return search.slots[a].size() < search.slots[b].size();
    }
    return search.slots[a][0].face_score > search.slots[b][0].face_score;
  });
  search.suffix_top.assign(slots_count + 1, 0);
  for (int i = slots_count - 1; i >= 0; --i) {
    int slot = search.ordered_slots[i];
    search.suffix_top[i] = search.suffix_top[i + 1] + search.slots[slot][0].face_score;
  }
  search.selected.assign(slots_count, -1);
  if (argc >= 5) {
    std::ifstream prices_file(argv[4]);
    std::array<long long, 26> prices{};
    if (!(prices_file >> search.price_scale) || search.price_scale <= 0)
      throw std::runtime_error("invalid price scale");
    long long blank_allowance = 0;
    for (int a = 0; a < 26; ++a) {
      if (!(prices_file >> prices[a]) || prices[a] < 0)
        throw std::runtime_error("invalid nonnegative letter price");
      blank_allowance = std::max(blank_allowance, prices[a] - search.price_scale * kLetterValues[a]);
    }
    search.resource_upper = search.price_scale * search.main_face + 2 * blank_allowance;
    for (int a = 0; a < 26; ++a)
      search.resource_upper += prices[a] * (kTileDistribution[a] - search.main_counts[a]);
    for (auto& slot : search.slots) {
      long long top = -1000000000000000LL;
      for (const auto& option : slot) {
        long long reduced = search.price_scale * option.face_score;
        for (int a = 0; a < 26; ++a) reduced -= prices[a] * option.counts_without_new[a];
        top = std::max(top, reduced);
      }
      search.resource_upper += top;
      for (auto& option : slot) {
        long long reduced = search.price_scale * option.face_score;
        for (int a = 0; a < 26; ++a) reduced -= prices[a] * option.counts_without_new[a];
        option.reduced_loss = top - reduced;
      }
    }
    search.use_prices = true;
    std::cout << "resource_upper_numerator " << search.resource_upper << "\nprice_scale " << search.price_scale << "\n";
  }
  score_after_best_blanks(search.main_face, search.main_entries, search.slots,
                         search.selected, &search.mandatory_main_penalty);
  search.started = std::chrono::steady_clock::now();
  search.last_report = search.started;
  search.dfs(0, search.main_face, search.main_counts);
  double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - search.started).count();

  std::cout << "final best " << search.best << "\n";
  std::cout << "nodes " << search.nodes << "\n";
  std::cout << "leaves " << search.leaves << "\n";
  std::cout << "records_retained " << search.records.size() << "\n";
  std::cout << "elapsed_seconds " << elapsed << "\n";
  for (std::size_t rank = 0; rank < search.records.size(); ++rank) {
    const Record& record = search.records[rank];
    std::cout << "record " << (rank + 1) << " score " << record.score << " face "
              << record.face_score << " penalty " << record.penalty << " selection";
    for (int option_index : record.selected) {
      std::cout << ' ' << option_index;
    }
    std::cout << " words";
    for (std::size_t slot = 0; slot < record.selected.size(); ++slot) {
      int option_index = record.selected[slot];
      std::cout << ' ' << (option_index < 0 ? "." : search.slots[slot][option_index].word);
    }
    std::cout << " crosses";
    for (std::size_t slot = 0; slot < record.selected.size(); ++slot) {
      int oi = record.selected[slot];
      if (oi < 0) std::cout << " | .:0:0:0";
      else {
        const auto& option = search.slots[slot][oi];
        std::cout << " | " << option.word << ':' << option.face_score << ':' << option.start_row << ':' << option.index;
      }
    }
    std::cout << "\n";
  }
  return 0;
}
