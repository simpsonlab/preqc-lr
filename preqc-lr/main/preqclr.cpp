#include <algorithm>
#include <chrono>
#include <fstream>
#include <functional>
#include <iostream>
#include <list>
#include <map>
#include <math.h>
#include <sstream>
#include <string>
#include <vector>

#include <limits.h>
#include "preqclr.hpp"

#include <zlib.h>
#include <stdio.h>
#include <getopt.h>

#include "seqtk/kseq.h"
#include "readpaf/paf.h"
#include "readpaf/sdict.h"

#include "zstr.hpp"
#include "strict_fstream.hpp"

#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/prettywriter.h"
#include "rapidjson/filereadstream.h"
#include "rapidjson/filewritestream.h"

KSEQ_INIT(gzFile, gzread)

#define VERSION "2.0"
#define SUBPROGRAM "calculate"

using namespace std;
using namespace rapidjson;

typedef PrettyWriter<StringBuffer> JSONWriter;
typedef std::chrono::duration<float> fsec;

bool myComparison(const pair<double,int> &a,const pair<double,int> &b)
{
       return a.second<b.second;
}

namespace opt
{
    static unsigned int verbose;
    static string reads_file;
    static string paf_file;
    static string gfa_file = "";
    static string type;
    static string sample_name;
}

int main( int argc, char *argv[]) 
{
    // parse the input arguments, if successful it will save all the arguments
    // in the global struct opts
    parse_args(argc, argv);

    // Let's handle the verbose option
    // SO: https://stackoverflow.com/questions/10150468/how-to-redirect-cin-and-cout-to-files
    if ( opt::verbose != 1 ) {
        // if verbose option not found, then redirect all cout to preqclr.log file
        ofstream out( "preqclr.log" );
        streambuf *coutbuf = cout.rdbuf();
        cout.rdbuf(out.rdbuf());
    }
    cout << "========================================================" << endl;
    cout << "RUNNING PREQC-LR CALCULATE" << endl;
    cout << "========================================================" << endl;
    auto tot_start = chrono::system_clock::now();
    auto tot_start_cpu = clock();
 
    // parse the input PAF file and return a map with key = read id, 
    // and value = read object with all needed read info
    // SO: https://stackoverflow.com/questions/11062804/measuring-the-runtime-of-a-c-code
    // SO1 to get cast to milliseconds: https://stackoverflow.com/questions/30131181/calculate-time-to-execute-a-function 
    cout << "[ Parse PAF file ] " << endl;
    auto swc = chrono::system_clock::now();    
    auto scpu = clock();
    map<string, sequence> paf_records = parse_paf();
    auto ewc = chrono::system_clock::now();
    auto ecpu = clock();
    fsec elapsedwc = ewc - swc;
    double elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;

    // start json object
    StringBuffer s;
    JSONWriter writer(s);
    writer.StartObject();

    // add input arguments
    writer.String("sample_name");
    writer.String(opt::sample_name.c_str());

    // start calculations
    // SO: Calculating CPU time. (https://stackoverflow.com/questions/17432502/how-can-i-measure-cpu-time-and-wall-clock-time-on-both-linux-windows)
    swc = chrono::system_clock::now();
    scpu = clock();
    cout << "[ Calculating read length distribution ]" << endl;
    calculate_read_length( paf_records, &writer);
    ewc = chrono::system_clock::now();
    ecpu = clock();
    elapsedwc = ewc - swc;
    elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;

    cout << "[ Calculating est cov per read and est genome size ]" << endl;
    swc = chrono::system_clock::now();
    scpu = clock();
    int genome_size_est = calculate_est_cov_and_est_genome_size( paf_records, &writer);
    ewc = chrono::system_clock::now();
    ecpu = clock();
    elapsedwc = ewc - swc;
    elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;

    cout << "[ Calculating GC-content per read ]" << endl;
    swc = chrono::system_clock::now();
    scpu = clock();
    calculate_GC_content( opt::reads_file, &writer);
    ewc = chrono::system_clock::now();
    ecpu = clock();
    elapsedwc = ewc - swc;
    elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;

    cout << "[ Calculating total number of bases as a function of min read length ]" << endl;
    swc = chrono::system_clock::now();
    scpu = clock();
    calculate_tot_bases( paf_records, &writer);
    ewc = chrono::system_clock::now();
    ecpu = clock();
    elapsedwc = ewc - swc;
    elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;

    if ( !opt::gfa_file.empty() ) {
        cout << "[ Parse GFA file ] " << endl;
        swc = chrono::system_clock::now();
        scpu = clock();
        vector<int> contigs = parse_gfa();
        ewc = chrono::system_clock::now();
        ecpu = clock();
        elapsedwc = ewc - swc;
        elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
        cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;


        cout << "[ Calculating NGX ]" << endl;
        swc = chrono::system_clock::now();
        scpu = clock();
        calculate_ngx( contigs, genome_size_est, &writer );
        ewc = chrono::system_clock::now();
        ecpu = clock();
        elapsedwc = ewc - swc;
        elapsedcpu = (ecpu - scpu)/(double)CLOCKS_PER_SEC;;
        cout << "[+] Time elapsed: " << elapsedwc.count() << "s, CPU time: "  << elapsedcpu << "s" << endl;
    }
    // convert JSON document to string and print
    writer.EndObject();
    ofstream preqclrFILE;
    string filename = opt::sample_name + ".preqclr"; 
    preqclrFILE.open( filename );
    preqclrFILE << s.GetString() << endl;
    preqclrFILE.close();
 
    // wrap it up
    cout << "[ Done ]" << endl;
    cout << "[+] Resulting preqclr file: " << filename << endl;
    auto tot_end = chrono::system_clock::now();
    auto tot_end_cpu = clock();
    fsec tot_elapsed = tot_end - tot_start;
    double tot_elapsed_cpu = (tot_end_cpu - tot_start_cpu)/(double)CLOCKS_PER_SEC;;
    cout << "[+] Total time: " << tot_elapsed.count() << "s, CPU time: "  << tot_elapsed_cpu << "s" << endl;
}

vector<int> parse_gfa()
{
    // parse gfa to get the contig lengths
    string line;
    ifstream infile(opt::gfa_file);
    if (!infile.is_open()) {
        fprintf(stderr, "preqclr %s: GFA failed to open. Check to see if it exists, is readable, and is non-empty.\n\n", SUBPROGRAM);
        exit(1);
    }
    vector <int> contig_lengths;
    while( getline(infile, line) ) {
        char spec;
        stringstream ss(line);
        ss >> spec;

        // get only lines that have information on the contig length
        if ( spec == 'S' ) {
            string contig_id, contig_seq, contig_len;
            ss >> spec >> contig_id >> contig_seq >> contig_len;
            const string toErase = "LN:i:";
            size_t pos = contig_len.find(toErase);

            // Search for the substring in string in a loop untill nothing is found
            if (pos != string::npos)
            {
                // If found then erase it from string
                contig_len.erase(pos, toErase.length());
            }
            int len = stoi(contig_len);
            contig_lengths.push_back(len);
        }
    }
    return contig_lengths;
}

void parse_args ( int argc, char *argv[])
{
    // getopt
    extern char *optarg;
    extern int optind, opterr, optopt;
    const char* const short_opts = ":g:hvr:t:n:p:";
    const option long_opts[] = {
        {"verbose",         no_argument,        NULL,   'v'},
        {"version",         no_argument,        NULL,   OPT_VERSION},
        {"reads",           required_argument,  NULL,   'r'},
        {"type",            required_argument,  NULL,   't'},
        {"sample_name", required_argument,  NULL,   'n'},
        {"paf",         required_argument,  NULL,   'p'},
        {"gfa",         required_argument,  NULL,   'g'},
        {"help",            no_argument,    NULL,   'h'},
        { NULL,         0,  NULL,   0}
    };

    static const char* PREQCLR_CALCULATE_VERSION_MESSAGE =
    "preqclr-" SUBPROGRAM " version " VERSION "\n"
    "Written by Joanna Pineda.\n"
    "\n"
    "Copyright 2017 Ontario Institute for Cancer Research\n";

    static const char* PREQCLR_CALCULATE_USAGE_MESSAGE =
    "Usage: preqclr version " VERSION " " SUBPROGRAM " [OPTIONS] --reads reads.fa --type {ont|pb} --paf overlaps.paf --gfa layout.gfa \n"
    "Calculate information for preqclr report\n"
    "\n"
    "-v, --verbose				display verbose output\n"
    "    --version				display version\n"
    "-r, --reads				Fasta, fastq, fasta.gz, or fastq.gz files containing reads\n"
    "-t, --type				Type of long read sequencer. Either pacbio (pb) or oxford nanopore technology data (ont)\n"
    "-n, --sample_name			Sample name; you can use the name of species for example. This will be used as output prefix\n"
    "-p, --paf				Minimap2 pairwise alignment file (PAF). This is produced using \'minimap2 -x ava-ont sample.fastq sample.fasta"
    "\n"
    "-g, --gfa				Miniasm graph fragment assembly (GFA) file. This file is produced using \'miniasm -f reads.fasta overlaps.paf\'\n"
    "\n";

    int rflag=0, tflag=0, nflag=0, pflag=0, gflag=0, verboseflag=0, versionflag=0;
    int c;
    while ( (c = getopt_long(argc, argv, short_opts, long_opts, NULL)) != -1 ) {
    // getopt will loop through arguments, returns -1 when end of options, and store current arg in optarg
    // if optarg is not null, keep as optarg else ""
    std::istringstream arg(optarg != NULL ? optarg : "");
    switch(c) {
        case 'v':
            opt::verbose = 1; // set verbose flag
            break;
        case OPT_VERSION:
            cout << PREQCLR_CALCULATE_VERSION_MESSAGE << endl;
            exit(0);
        case 'r':
            if ( rflag == 1 ) {
                fprintf(stderr, "preqclr %s: multiple instances of option -r,--reads. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]); 
                exit(1);
            }
            rflag = 1;
            arg >> opt::reads_file;
            break;
        case 't':
            if ( tflag == 1 ) {
                fprintf(stderr, "preqclr %s: multiple instances of option -t,--type. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
                exit(1);
            }
            tflag = 1;
            if (( arg.str().compare("ont")    != 0 ) && ( arg.str().compare("pb") != 0 )) {
                fprintf(stderr, "preqclr %s: option -t,--type is missing a valid argument {ont,pb}. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
                exit(1);
            }
            arg >> opt::type;
            break;
        case 'n':
            if ( nflag == 1 ) {
                fprintf(stderr, "preqclr %s: multiple instances of option -n,--sample_name. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
                exit(1);
            }
            nflag = 1;
            arg >> opt::sample_name;
            break;
        case 'p':
            if ( pflag == 1 ) {
                fprintf(stderr, "preqclr %s: multiple instances of option -p,--paf. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
                exit(1);
            }
            pflag = 1;
            arg >> opt::paf_file;
            break;
        case 'g':
            if ( gflag == 1 ) {
                fprintf(stderr, "preqclr %s: multiple instances of option -g,--gfa. \n\n", SUBPROGRAM);
                fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
                exit(1);
            }
            gflag = 1;
            arg >> opt::gfa_file;
            break;
        case 'h':
            cout << PREQCLR_CALCULATE_USAGE_MESSAGE << endl;
            exit(0);
        case ':':
            fprintf(stderr, "preqclr %s: option `-%c' is missing a required argument\n", SUBPROGRAM, optopt);
            fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
            exit(1);
        case '?':
            // invalid option: getopt_long already printed an error message
            fprintf(stderr, "preqclr %s: option `-%c' is invalid: ignored\n", SUBPROGRAM, optopt);
            fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
            break;
        }
    }
    if( argc < 4 ) {
        cerr << PREQCLR_CALCULATE_USAGE_MESSAGE << endl;
        exit(1);
    }

    // print any remaining command line arguments
    if (optind < argc) {
        for (; optind < argc; optind++)
            cerr << "preqclr " << SUBPROGRAM << ": too many arguments: "
                 << argv[optind] << endl;
    }

    // check mandatory variables and assign defaults
    if ( rflag == 0 ) {
        fprintf(stderr, "preqclr %s: missing -r,--reads option\n\n", SUBPROGRAM);
        fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE, argv[0]);
        exit(1);
    }
    if ( nflag == 0 ) {
        fprintf(stderr, "preqclr %s: missing -n,--sample_name option\n\n", SUBPROGRAM);
        fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE);
        exit(1);
    }
    if ( pflag == 0 ) {
        fprintf(stderr, "preqclr %s: missing -p,--paf option\n\n", SUBPROGRAM);
        fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE);
        exit(1);
    }
    if ( tflag == 0 ) {
        fprintf(stderr, "preqclr %s: missing -t,--type option\n\n", SUBPROGRAM);
        fprintf(stderr, PREQCLR_CALCULATE_USAGE_MESSAGE);
        exit(1);
    }

};

map<string, sequence> parse_paf()
{
    // read each line in paf file passed on by user
    string line;
    const char *c = opt::paf_file.c_str();
    paf_file_t *fp;
    paf_rec_t r;
    sdict_t *d;
    fp = paf_open(c);
    if (!fp) {
        fprintf(stderr, "ERROR: could not open PAF file %s\n", __func__, c);
        exit(1);
    }
    d = sd_init();

    map<string, sequence> paf_records;
    while (paf_read(fp, &r) >= 0) { 

        // read each line/overlap and save each column into variable
        string qname = r.qn;
        unsigned int qlen = r.ql;
        unsigned int qstart = r.qs;
        unsigned int qend = r.qe;
        unsigned int strand = r.rev;
        string tname = r.tn;
        unsigned int tlen = r.tl;
        unsigned int tstart = r.ts;
        unsigned int tend = r.te

        if ( qname.compare(tname) != 0 ) {
            unsigned int qprefix_len = qstart;
            unsigned int qsuffix_len = qlen - qend - 1;
            unsigned int tprefix_len = tstart;
            unsigned int tsuffix_len = tlen - tend - 1;

            // calculate overlap length, we need to take into account minimap2's softclipping
            int left_clip = 0, right_clip = 0;
            if ( ( qstart != 0 ) && ( tstart != 0 ) ){
                if ( strand == 0 ) {
                    left_clip += min(qprefix_len, tprefix_len);
                } else {
                    left_clip += min(qprefix_len, tsuffix_len);
                }
            }
            if ( ( qend != 0 ) && ( tend != 0 ) ){
                if ( strand == 0 ) {
                    right_clip += min(qsuffix_len, tsuffix_len);
                } else {
                    right_clip += min(qsuffix_len, tprefix_len);
                }
            }
            
            unsigned int overlap_len = abs(qend - qstart) + left_clip + right_clip;
  
            // add this information to paf_records dictionary
            auto i = paf_records.find(qname);
            if ( i == paf_records.end() ) {
                // if read not found initialize in paf_records
                sequence qr;
                double cov = double(overlap_len) / double(qlen);
                qr.set(qname, qlen, cov);
                paf_records.insert(pair<string,sequence>(qname, qr));
            } else {
                // if read found, update the overlap info
                double cov = double(overlap_len) / double(qlen);
                i->second.updateCov(cov);
            }
            auto j = paf_records.find(tname);
            if ( j == paf_records.end() ) {
                // if target read not found initialize in paf_records
                sequence tr;
                double cov = double(overlap_len) / double(tlen);
                tr.set(tname, tlen, cov);
                paf_records.insert(pair<string,sequence>(tname, tr));
            } else {
                // if target read found, update the overlap info
                double cov = double(overlap_len) / double(tlen);
                j->second.updateCov(cov);
            }
        }
    }
    
   return paf_records;
}

void calculate_ngx( vector<int> contig_lengths, int genome_size_est, JSONWriter* writer ){
    /*
    ========================================================
    Calculating NGX
    --------------------------------------------------------
    Uses GFA information to evaluate the assembly quality
    Input:      All the contig lengths
    Output:     NGX values in a dictionary:
                key   = X
                value = contig length where summing contigs 
                with length greater than or equal to this 
                length is Xth percentile
                of the genome size estimate....
    ========================================================
    */
    int x = 0;
    int nx;
    // this is going to hold key = x percent of genome size estimate, value = x
    map<unsigned long long int, int> gx;
    while ( x <= 100 ) {
        gx.insert( make_pair((float(x) * genome_size_est)/100, x) );
        x += 1;
    }
    
    // sort in descending order the contig_lengths
    sort(contig_lengths.rbegin(), contig_lengths.rend());
   
    // this is going to hold key = x, value = ngx
    map<int, int> ngx;
    int start = 0, end = 0;
    for ( auto const& c : contig_lengths ) {
       end += c;
       // for all values that are less then the curr sum
       for ( auto& p : gx ) {
           if ( ( p.first >= start ) && ( p.first <= end ) ) {
               ngx.insert( make_pair(p.second, c) );
           }           
       }
       start += c;
    }

    writer->Key("ngx_values");
    writer->StartObject();
    for ( auto& p : ngx ) {
        string key = to_string(p.first);
        // x value:
        writer->Key(key.c_str());
        // ngx value:
        writer->Int(p.second);
    }
    writer->EndObject();   
}

void calculate_tot_bases( map<string, sequence> paf, JSONWriter* writer)
{
    /*
    ========================================================
    Calculating total number of bases as a function of 
    min read length
    --------------------------------------------------------
    Shows the total number of bases with varying minimum 
    read length cut offs.
    Input:      Dictionary of reads with read length info in value
    Output:     Dictionary:
                key   = read length cut off
                value = total number of bases
    ========================================================
    */

    // bin the reads by read length, and sort in decreasing order
    map < unsigned int, int, greater<unsigned int>> read_lengths;
    for( auto it = paf.begin(); it != paf.end(); it++) {
        string id = it->first;
        unsigned int r_len = it->second.read_len;

        // add as new read length if read length not in map yet
        auto j = read_lengths.find(r_len);
        if ( j == read_lengths.end() ) {
            // if read length not found
            read_lengths.insert( pair<unsigned int,int>(r_len, 1) );
        } else {
            // if read length found
            j->second += 1;
        }
    }

    writer->Key("total_num_bases_vs_min_read_length");
    writer->StartObject();
    unsigned long long curr_longest;
    unsigned int nr;       // number of reads with read length
    unsigned long long nb; // total number of bases of reads with current longest read length
    unsigned long long tot_num_bases = 0;
    for (const auto& p : read_lengths) {
        curr_longest = p.first;
        nr = p.second;
        nb = curr_longest * nr;
        cout << curr_longest << endl;
        // detect for potential overflow issues:
        // SO: https://stackoverflow.com/questions/199333/how-to-detect-integer-overflow
        // curr_longest * nr may have encountered an overflow issue
        //     leading to a negative number. We do not include negative nb. 
            if (!(nb > 0) || !(tot_num_bases > INT_MAX - nb)) {
                // would not overflow 
                tot_num_bases += nb;
                string key = to_string( curr_longest );
                writer->Key(key.c_str());
                writer->Int(tot_num_bases);
            }
    }
    writer->EndObject();
}

void calculate_GC_content( string file, JSONWriter* writer )
{
    /*
    ========================================================
    Calculating GC-content per read
    --------------------------------------------------------
    Parses through read file and counts the Cs and Gs,
    then divides by the read length.
    Input:     Path to reads FILE
    Output:    List of GC content of all reads
    ========================================================
    */

    vector < double > GC_content;
    gzFile fp;
    kseq_t *seq;
    const char *c = file.c_str();
    fp = gzopen(c, "r");
    if (fp == 0) {
        fprintf(stderr, "preqclr %s: reads file failed to open. Check to see if it exists, is readable, and is non-empty.\n\n", SUBPROGRAM);
        exit(1);
    }
    seq = kseq_init(fp);
    writer->Key("read_counts_per_GC_content");
    writer->StartArray();
    while (kseq_read(seq) >= 0) {
         string id = seq->name.s;
         string sequence = seq->seq.s;
         size_t C_count = count(sequence.begin(), sequence.end(), 'C');
         size_t G_count = count(sequence.begin(), sequence.end(), 'G');
         double r_len = sequence.length();
         double gc_cont = (double( C_count + G_count ) / r_len) *100.0;
         writer->Double(gc_cont);
    }
    writer->EndArray();
    kseq_destroy(seq);
    gzclose(fp); 
}

float calculate_est_cov_and_est_genome_size( map<string, sequence> paf, JSONWriter* writer )
{
    /*
    ========================================================
    Calculating est cov per read and est genome size
    --------------------------------------------------------
    For each read uses length and sum of lengths of all 
    overlaps.
    Input:    PAF records dictionary
    Output:   Dictionary: (each entry is a read)
              key = est coverage
              value = read length 
    ========================================================
    */

    vector<pair <double, int>> covs;

    // make an object that will hold pair of coverage and read length
    writer->Key("per_read_est_cov_and_read_length");
    writer->StartObject();
    for( auto it = paf.begin(); it != paf.end(); it++)
    {
        string id = it->first;
        sequence r = it->second;
        double r_len = r.read_len;
        double r_cov = r.cov;
        string key = to_string(r_cov);
        //cout << r_len << endl;
        writer->Key(key.c_str());
        writer->Int(r_len);
        covs.push_back(make_pair(round(r_cov),r_len));        
    }
    writer->EndObject();

    cout << "done" << endl;

    // filter the coverage: remove if outside 1.5*interquartile_range
    // calculate IQR
    // sort the estimated coverages
    sort(covs.begin(), covs.end());

    cout << "done" << endl;
    // get the index of the 25th and 75th percentile item
    int i25 = ceil(covs.size() * 0.25);
    int i75 = ceil(covs.size() * 0.75);
    
    double IQR = covs[i75].first - covs[i25].first;
    double bd = IQR*1.5;
    double lowerbound = round(double(covs[i25].first) - bd);
    double upperbound = round(double(covs[i75].first) + bd);
    //cout << IQR << ", lb" << lowerbound << ", ub" << upperbound << endl;

    // create a new set after applying this filter
    // stores info of set of reads after filtering:
    long long sum_len = 0;
    long double sum_cov = 0;
    int tot_reads = 0;
    vector <double> filtered_covs;
    for( auto it = covs.begin(); it != covs.end(); ++it ) {
        double co = round(it->first);
        if (( co > lowerbound ) && ( co < upperbound )) {
            unsigned long long le = it->second;
            sum_len += le;
            sum_cov += co;
            tot_reads += 1;
            filtered_covs.push_back(co);
        }
    }
    // get the median coverage
    sort(filtered_covs.begin(), filtered_covs.end());
    cout << "size: " <<  filtered_covs.size() << endl;
    int i50 = ceil(filtered_covs.size() * 0.50);
    double median_cov = double(filtered_covs[i50]);

    // calculate estimated genome size
    double mean_read_len = double(sum_len) / double(tot_reads);
    double est_genome_size = ( tot_reads * mean_read_len ) / median_cov;
    //cout << "median cov: " << median_cov << endl;
    //cout << "mean read length: " << mean_read_len << endl;
    //cout << "est genome size: " << est_genome_size << endl;

    // now store in JSON object
    writer->Key("est_cov_post_filter_info");
    writer->StartArray();
    writer->Double(lowerbound);
    writer->Double(upperbound);
    writer->Int(tot_reads);
    writer->Double(IQR);
    writer->EndArray();
    writer->Key("est_genome_size");
    writer->Double(est_genome_size);    
    return est_genome_size;
}

void calculate_read_length( map<string, sequence> paf, JSONWriter* writer)
{
    /*
    ========================================================
    Calculating read lengths
    --------------------------------------------------------
    For each read add read lengths to JSON object
    Input:        PAF records dictionary
    Output:     List of all read lengths
    ========================================================
    */

    writer->Key("per_read_read_length");
    writer->StartArray();

    // loop through the map of reads and get read lengths
    for(auto it = paf.begin(); it != paf.end(); it++) {
        sequence r = it->second;
        int r_len = r.read_len;
        writer->Int(r_len);
    }
    writer->EndArray();
}
