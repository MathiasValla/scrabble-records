#include <algorithm>
#include <array>
#include <chrono>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

// All scores exclude the bingo. No bag or partial-board legality pruning occurs.
constexpr int values[26] = {1,3,3,2,1,4,2,4,1,8,5,1,3,1,1,3,10,1,1,1,1,4,4,8,4,10};
struct Record { int upper, main, row, start; std::string word; std::vector<int> holes; };

int main(int argc, char** argv) {
  if (argc != 5) { std::cerr << "usage: scan_k_upper WORDS K PREBONUS_THRESHOLD OUTPUT\n"; return 2; }
  const int k = std::stoi(argv[2]), threshold = std::stoi(argv[3]);
  if (k < 2 || k > 7) throw std::runtime_error("K must be 2..7");
  std::ifstream input(argv[1]);
  if (!input) throw std::runtime_error("missing lexicon");
  std::unordered_set<std::string> legal;
  std::string w;
  while (input >> w) {
    if (w.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZ") != std::string::npos)
      throw std::runtime_error("non-uppercase lexicon entry");
    legal.insert(w);
  }
  std::vector<std::string> words(legal.begin(), legal.end());
  std::sort(words.begin(), words.end());
  int lm[225], wm[225];
  std::fill(lm, lm+225, 1); std::fill(wm, wm+225, 1);
  for (int p : {0,7,14,105,119,210,217,224}) wm[p]=3;
  for (int p : {16,28,32,42,48,56,64,70,112,154,160,168,176,182,192,196,208}) wm[p]=2;
  for (int p : {20,24,76,80,84,88,136,140,144,148,200,204}) lm[p]=3;
  for (int p : {3,11,36,38,45,52,59,92,96,98,102,108,116,122,126,128,132,165,172,179,186,188,213,221}) lm[p]=2;
  auto good = [&](const std::string& s, int a, int b) {
    return b-a <= 1 || legal.count(s.substr(a,b-a));
  };
  int cross_base[26][15] = {};
  long long cross_raw=0, cross_kept=0, playable=0;
  for (const auto& s : words) {
    int n=s.size(), base=0;
    if(n<2 || n>15) continue;
    ++playable;
    for(char ch:s) base+=values[ch-'A'];
    for(int i=0;i<n;++i) {
      ++cross_raw;
      if(!good(s,0,i) || !good(s,i+1,n)) continue;
      ++cross_kept;
      for(int row=i;row<=15-n+i;++row)
        cross_base[s[i]-'A'][row]=std::max(cross_base[s[i]-'A'][row],base);
    }
  }
  int cross[26][225] = {};
  for(int a=0;a<26;++a) for(int p=0;p<225;++p)
    cross[a][p]=wm[p]*(cross_base[a][p/15]+(lm[p]-1)*values[a]);
  std::vector<Record> survivors;
  long long raw=0, kept=0, placements=0;
  auto begin=std::chrono::steady_clock::now(), report=begin;
  for(const auto& s:words) {
    int n=s.size(), base=0;
    if(n<k || n>15) continue;
    for(char ch:s) base+=values[ch-'A'];
    bool fragment[16][16] = {};
    for(int a=0;a<=n;++a) for(int b=a;b<=n;++b) fragment[a][b]=good(s,a,b);
    std::vector<int> holes(k);
    std::function<void(int,int)> choose = [&](int depth,int next) {
      if(depth<k) {
        for(int i=next;i<=n-(k-depth);++i) { holes[depth]=i; choose(depth+1,i+1); }
        return;
      }
      ++raw;
      int previous=0;
      for(int i:holes) { if(!fragment[previous][i]) return; previous=i+1; }
      // The terminal empty fragment is legal, including when the last tile is new.
      if(!fragment[previous][n]) return;
      ++kept;
      for(int row=0;row<15;++row) for(int start=0;start<=15-n;++start) {
        ++placements;
        int mult=1, bonus=0, crosses=0;
        for(int i:holes) {
          int p=row*15+start+i, a=s[i]-'A';
          mult*=wm[p]; bonus+=(lm[p]-1)*values[a]; crosses+=cross[a][p];
        }
        int main=mult*(base+bonus), upper=main+crosses;
        if(upper>=threshold) survivors.push_back({upper,main,row+1,start+1,s,holes});
      }
    };
    choose(0,0);
    auto now=std::chrono::steady_clock::now();
    if(std::chrono::duration<double>(now-report).count()>20) {
      std::cerr<<"k="<<k<<" word="<<s<<" placements="<<placements<<" survivors="<<survivors.size()
        <<" elapsed="<<std::chrono::duration<double>(now-begin).count()<<"s\n";
      report=now;
    }
  }
  std::sort(survivors.begin(),survivors.end(),[](const Record&a,const Record&b){
    if(a.upper!=b.upper) return a.upper>b.upper;
    if(a.word!=b.word) return a.word<b.word;
    if(a.row!=b.row) return a.row<b.row;
    if(a.start!=b.start) return a.start<b.start;
    return a.holes<b.holes;
  });
  std::ofstream out(argv[4]);
  if(!out) throw std::runtime_error("cannot open output");
  out<<"k "<<k<<"\nthreshold "<<threshold<<"\nword_count "<<words.size()<<"\nplayable_words "<<playable
    <<"\nraw_cross "<<cross_raw<<"\ndeletion_valid_cross "<<cross_kept<<"\nraw_main_choices "<<raw
    <<"\ndeletion_valid_main_choices "<<kept<<"\nmain_placements "<<placements
    <<"\nindependent_upper_at_least_threshold "<<survivors.size()<<"\n";
  for(size_t j=0;j<survivors.size();++j) {
    const auto&r=survivors[j];
    out<<"top "<<j+1<<" upper "<<r.upper<<" main "<<r.main<<" word "<<r.word<<" indices";
    for(int i:r.holes) out<<" "<<i+1;
    out<<" row "<<r.row<<" start "<<r.start<<"\n";
  }
  std::cerr<<"DONE k="<<k<<" raw="<<raw<<" kept="<<kept<<" placements="<<placements
    <<" survivors="<<survivors.size()<<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"\n";
}
