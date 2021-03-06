#!/usr/bin/env python
# ========================================================
# preqclr report:
# Generates PDF visualizing genome characteristics
# ========================================================
try:
    from Bio import SeqIO
    import subprocess, math, argparse
    import matplotlib as MPL
    MPL.use('Agg')
    import numpy as np
    from matplotlib.backends.backend_pdf import PdfPages
    import pylab as plt
    import sys, os, csv
    import json
    import time
    import collections
    import operator
    from mpl_toolkits.axes_grid1 import make_axes_locatable
except ImportError:
    print('Missing package(s)')    
    quit()

plots_available = ['est_genome_size', 'read_length_dist', 'est_cov_dist', 'per_read_GC_content_dist', 'total_num_bases_vs_min_read_length', 'dust_score', 'overlap_lengths', 'indel_error_rates']
save_png=False
max_percentile=90
log=list()
verbose=False

def main():
    # --------------------------------------------------------
    # PART 0: Pre-process arguments
    # --------------------------------------------------------
    parser = argparse.ArgumentParser(description='Generate preqclr PDF report', usage=msg(), add_help=False)
    parser.add_argument("-h", "--help", action="store_true", dest="help")
    parser.add_argument('-i', '--input', action="store", required=True, dest="preqc_file", nargs='+', help="preqclr file(s)")
    parser.add_argument('-o', '--output', action="store", dest="output_prefix", 
                        help="Prefix for output pdf")
    parser.add_argument('--plot', action="store", required=False, dest="plots_requested", nargs='+', choices=plots_available, 
                        help="Request plots by name")
    parser.add_argument('--list_plots', action="store_true", dest="list_plots", default=False, 
                        help="Use to see the plots available")
    parser.add_argument('--save_png', action="store_true", dest="save_png", default=False, 
                        help="Use to save png for each plot")
    parser.add_argument('--verbose', action="store_true", dest="verbose", 
                        help="Use to print progress to stdout")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 2.0')
    args = parser.parse_args()

    # print custom help message
    if args.help:
        parser.print_usage()

    # list plots if requested
    if args.list_plots:
        i = 1
        print "List of available plots: "
        for p in plots_available:
            print '\t' + str(i) + ". " + p
            i+=1 
        print "Use --plot and names to choose which plots to create."
        sys.exit(0)

    # check to see if preqclr files end with .preqclr
    for file in args.preqc_file:
        if not file.endswith('.preqclr'):
            print "ERROR: " + file + " does not end with .preqclr extension."
            sys.exit(1)

    # change output_prefix to prefix of preqclr file if not specified
    if not args.output_prefix and len(args.preqc_file) == 1:
        basename=os.path.basename(args.preqc_file[0])
        output_prefix=os.path.splitext(basename)[0]
    elif not args.output_prefix and len(args.preqc_file) > 1:
        output_prefix="default"
    else:
        output_prefix=args.output_prefix

    # save global variable verbose flag
    if args.verbose:
        global verbose
        verbose=True

    custom_print( "========================================================" )
    custom_print( "Run preqclr report" )
    custom_print( "========================================================" )

    # set global variable of save png
    global save_png
    if args.save_png:
        save_png=True
        png_dir = "./" + output_prefix + "/png/"
        if not os.path.exists(png_dir):
            os.makedirs(png_dir)

    # list plots to make
    plots = list()
    if args.plots_requested:
        plots = args.plots_requested
    else:
        # if user did not specify plots, make all plots
        plots = plots_available

    if len(args.preqc_file) > 7:
        print "ERROR: Maximum amount of samples is 7. More than this will not display well."
        sys.exit(1)

    start = time.clock()
    create_report(output_prefix, args.preqc_file, plots)
    end = time.clock()
    total_time = end - start

    # --------------------------------------------------------
    # Final: Store log in file if user didn't specify verbose
    # --------------------------------------------------------
    custom_print("[ Store info]")
    custom_print("[+] preqclr report pdf: " + output_prefix + ".pdf")
    custom_print("[ Done ]")
    custom_print("[+] Total time: " + str(total_time) + " seconds" )
    global log
    outfile = output_prefix + ".preqclr-report.log"
    with open(outfile, 'wb') as f:
        for o in log:
            f.write(o + "\n")
    
def msg(name=None):                                                            
    return '''preqclr-report.py [OPTIONS] -i sample.preqclr
Generate PDF report with quality statistics 

    -i, --input=FILE              preqclr FILE(s)
    -o, --output                  Prefix for output pdf [default]
    --plot <plot1> <plot2> ...    Request plots by name {est_genome_size,read_length_dist,est_cov_dist,per_read_GC_content_dist,total_num_bases_vs_min_read_length}
    --list_plots                  Use to see the plots available
    --save_png                    Use to save png for each plot
    --verbose                     Use to print progress to stdout
    -v, --version                 Show program version number and exit

Report bugs to https://github.com/simpsonlab/preqclr/issues
        '''


def create_report(output_prefix, preqclr_file, plots_requested):

    # --------------------------------------------------------
    # PART 0: Configure the PDF file 
    # --------------------------------------------------------
    MPL.rc('figure', figsize=(8,10.5)) # in inches
    MPL.rc('font', size=11)
    MPL.rc('xtick', labelsize=6)
    MPL.rc('ytick', labelsize=6)
    MPL.rc('legend', fontsize=5)
    MPL.rc('axes', titlesize=10)
    MPL.rc('axes', labelsize=8)
    MPL.rcParams['lines.linewidth'] = 1.0

    # set PDF name
    output_pdf = output_prefix + ".pdf"
    pp = PdfPages(output_pdf)

    # --------------------------------------------------------
    # PART 1: Extract and save data from json file
    # --------------------------------------------------------
    est_genome_sizes = dict()
    per_read_read_length = dict()
    per_read_est_cov_and_read_length = dict()
    est_cov_post_filter_info = dict()
    peak_cov = dict()
    per_read_GC_content = dict()
    total_num_bases_vs_min_read_length = dict()
    ngx_values = dict()
    dust_scores = dict()
    overlap_lengths = dict()
    indel_error_rates = dict()

    # each sample will be represented with a unique marker and color
    markers = ['s', 'o', '^', 'p', '+', '*', 'v']
    colors = ['#FC614C', '#2DBDD8', '#B4E23D', '#F7C525', '#5B507A', '#0A2463', '#E16036' ] 

    # check to see if ngx values for any of the samples were found
    # in preqclr calculate, users needed to pass a GFA file in 
    # order for NGX values to be calculated
    ngx_calculated=False
    # check to see if DUST calculated (new feature)
    dust_calculated=False

    calcs = ['sample_name', 'est_genome_size', 'read_lengths', 'read_counts_per_GC_content', 'total_num_bases_vs_min_read_length', 'dust_scores', 'overlap_lengths', 'indel_error_rates']

    # start reading the preqclr file(s)
    for s_preqclr_file in preqclr_file:
        color = colors.pop(0)
        marker = markers.pop(0)
        with open(s_preqclr_file) as json_file:
            data = json.load(json_file)
            # check that all calculations were done
            for c in calcs:
                if not c in data.keys():
                    print "ERROR: " + c + " not calculated, try running the most recent version of preqclr calculate again."
                    sys.exit(1)
            # extract data for plots
            s = data['sample_name']
            est_genome_sizes[s] = (color, data['est_genome_size'], marker)
            per_read_read_length[s] = (color, data['read_lengths'], marker)
            per_read_est_cov_and_read_length[s] = (color, data['per_read_est_cov_and_read_length'], marker)
            est_cov_post_filter_info[s] = data['est_cov_post_filter_info']
            peak_cov[s] = data['mode_cov']
            per_read_GC_content[s] = (color, data['read_counts_per_GC_content'], marker)
            total_num_bases_vs_min_read_length[s] = (color, data['total_num_bases_vs_min_read_length'], marker)
            dust_scores[s] = (color, data['dust_scores'], marker)
            overlap_lengths[s] = (color, data['overlap_lengths'], marker)
            indel_error_rates[s] = (color, data['indel_error_rates'], marker)
            # check if ngx calculated
            if 'ngx_values' in data.keys():
                ngx_calculated=True
                ngx_values[s] = (color, data['ngx_values'], marker)
            # check if DUST score calculated
            if 'dust_scores' in data.keys():
                dust_calculated=True
                dust_scores[s] = (color, data['dust_scores'], marker)

    # --------------------------------------------------------
    # PART 2: Calculate the number of plots to be created
    # --------------------------------------------------------
    # total number of plots = a + b
    # a = number of plots in plots_requested not including ngx
    #     plots, est. cov vs read length, and tot_num_bases
    # b = number of samples with ngx values calculated
    # b += number of tot_num_bases plots (x2) = number of sumples
    # if est. cov vs read length requested, we need to create one for each sample

    # calculate num of samples
    num_ss = len(preqclr_file)

    # calculate a and b
    a = len(plots_requested)
    b = 0
    if 'total_num_bases_vs_min_read_length' in plots_requested:
        a -= 1
        b += num_ss
    # calculate the number of samples that had ngx_calculations
    if ngx_calculated:
        b+=1
    if dust_calculated:
        b+=1

    num_plots = a + b
    if num_plots > 6:
        num_plots +=1

    # --------------------------------------------------------
    # PART 3: Initialize the figures and subplots within
    # --------------------------------------------------------
    i = 0
    figs = list()
    subplots = list()

    while i < num_plots:
        # add figure
        fig = plt.figure()
        fig.suptitle("preqclr results : " + output_prefix )
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=0.5, hspace=0.5)

        # six subplots per pdf page
        ax1 = fig.add_subplot(321)
        ax2 = fig.add_subplot(322)
        ax3 = fig.add_subplot(323)
        ax4 = fig.add_subplot(324)
        ax5 = fig.add_subplot(325)
        ax6 = fig.add_subplot(326)

        subplots.extend((ax1, ax2, ax3, ax4, ax5, ax6))
        figs.append(fig)
        i+=6

    # parameters for saving each subplot as a png
    expand_x = 1.4
    expand_y = 1.28

    # --------------------------------------------------------
    # PART 4: Start plotting
    # --------------------------------------------------------
    num_plots_fin=0
    if 'est_genome_size' in plots_requested:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin > 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        num_plots_fin+=1
        ax = subplots.pop(0)
        ax_temp = plot_est_genome_size(ax, est_genome_sizes, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_est_genome_size.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)    
    if 'read_length_dist' in plots_requested:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin > 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        num_plots_fin+=1
        ax = subplots.pop(0)
        ax_temp = plot_read_length_distribution(ax, per_read_read_length, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_read_length_distribution.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if 'est_cov_dist' in plots_requested:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        num_plots_fin+=1
        ax = subplots.pop(0)
        ax_temp = plot_est_cov(ax, per_read_est_cov_and_read_length, est_cov_post_filter_info, peak_cov, output_prefix)
        ax.legend().set_title("mode:", prop={"size": 5})
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_est_cov.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if 'per_read_GC_content_dist' in plots_requested:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        num_plots_fin+=1
        ax = subplots.pop(0)
        ax_temp = plot_per_read_GC_content(ax, per_read_GC_content, output_prefix)
        ax.legend().set_title("mode:", prop={"size": 5})
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file =  "./" + output_prefix + "/png/plot_per_read_GC_content.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if 'total_num_bases_vs_min_read_length' in plots_requested:
        for s in total_num_bases_vs_min_read_length:
            if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
                ax = subplots.pop(0)
                plot_legend(ax, est_genome_sizes)
                num_plots_fin+=1
            num_plots_fin+=1
            ax = subplots.pop(0)
            ax_temp = plot_total_num_bases_vs_min_read_length(ax, total_num_bases_vs_min_read_length, s, output_prefix)
            if save_png:
                temp_fig = ax_temp.get_figure()
                extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
                ax_png_file = "./" + output_prefix + "/png/plot_total_num_bases_vs_min_read_length_" + s + ".png"
                temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if ngx_values and ngx_calculated:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        ax = subplots.pop(0)
        num_plots_fin+=1
        ax_temp = plot_ngx(ax, ngx_values, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_ngx.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if dust_calculated:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        ax = subplots.pop(0)
        num_plots_fin+=1
        ax_temp = plot_dust_scores(ax, dust_scores, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_dust_scores.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    if 'indel_error_rates' in plots_requested: 
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        ax = subplots.pop(0)
        num_plots_fin+=1
        ax_temp = plot_indel_error_rates(ax, indel_error_rates, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_indel_error_rates.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)   
    if 'overlap_lengths' in plots_requested:
        if ( num_ss > 1 and num_plots_fin%6 == 0 and num_plots_fin >= 6):
            ax = subplots.pop(0)
            plot_legend(ax, est_genome_sizes)
            num_plots_fin+=1
        ax = subplots.pop(0)
        num_plots_fin+=1
        ax_temp = plot_overlap_lengths(ax, overlap_lengths, output_prefix)
        if save_png:
            temp_fig = ax_temp.get_figure()
            extent = ax_temp.get_window_extent().transformed(temp_fig.dpi_scale_trans.inverted())
            ax_png_file = "./" + output_prefix + "/png/plot_overlap_lengths.png"
            temp_fig.savefig(ax_png_file, bbox_inches=extent.expanded(expand_x, expand_y), dpi=700)
    # --------------------------------------------------------
    # PART 5: Finalize the pdf file; save figs
    # --------------------------------------------------------
    for f in figs:
        f.savefig(pp, format='pdf', dpi=1000)

    pp.close()

def plot_legend(ax, data):
    # sample names
    s = []
    # colors
    c = []

    for n in data:
        s.append(n)
        c.append(MPL.lines.Line2D((0,0),(1,1),
                linestyle='-', marker=data[n][2],
                color=data[n][0]))

    ax.set_title("Legend", loc='left')
    ax.legend(c, s, loc=2, bbox_to_anchor=(0,1), borderaxespad=0)
    ax.tick_params(axis='x', which='both', bottom='off', top='off', labelbottom='off')
    ax.tick_params(axis='y', which='both', left='off', top='off', labelleft='off')
    ax.set_frame_on(False)

def plot_read_length_distribution(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting read length distribution ]" )
    # ========================================================
    global max_percentile
    read_lengths = data

    # now start plotting for each sample
    # get the maximum read length across all the samples
    max_read_length = 0
    y_lim = 0
    for s in read_lengths:
        s_name = s
        s_color = read_lengths[s][0]
        sd = read_lengths[s][1]

        base = 100
        sd_rounded = [ int(base * round(float(x)/base)) for x in sd ]
        labels, values = zip(*sorted(collections.Counter(sorted(sd_rounded)).items()))

        # normalize labels
        s = sum(values)
        nlabels = list()
        nvalues = list()
        for v in values:
            nv = float(v)/float(s)
            nvalues.append(nv)

        # get x and y limits
        if max(nvalues) > y_lim:
            y_lim = max(nvalues)*1.3
        s_max_read_length = max(sd_rounded)
        if s_max_read_length > max_read_length:
            max_read_length = s_max_read_length
            x_lim = np.percentile(sd_rounded, max_percentile)

        # plot!
        ax.plot(labels, [float(i) for i in nvalues], color=s_color, label=s_name)

    # configure the subplot
    ax.set_title('Read length distribution')
    ax.set_xlabel('Read lengths (bp)')
    ax.set_ylabel('Proportion')
    ax.set_xlim(0, x_lim)
    ax.set_ylim(0, y_lim)
    ax.grid(True, linestyle='-', linewidth=0.3)
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    return ax

def plot_est_cov(ax, data, filter_info, peak_cov, output_prefix):
    # ========================================================
    custom_print( "[ Plotting est cov per read ]" )
    # ========================================================

    max_cov = 0
    max_y = 0
    num_bins = 0
    for s in data:
        sd = data[s] # list of tuples (read_cov, read_len)
        sd_upperbound_cov = filter_info[s][1]
        sd_est_cov_read_length = data[s][1] # this returns a dictionary with key = est_cov and value
        sd_est_cov = [ round(float(x)) for x in sd_est_cov_read_length.keys() ]
        sd_mode_cov = peak_cov[s]
        s_name = s
        s_color = data[s][0]
        d = sorted(sd_est_cov)
        x, y = zip(*sorted(collections.Counter(sorted(sd_est_cov)).items()))

        # normalize y values and identify x limit
        sy = sum(y)
        ny = list()
        cm = 0
        p = 0
        lim = 0
        for i in y:
            ni = round(float(i)/sy,4)
            ny.append(ni)
            cm += i
            p += 1
            # get 90th percentile
            if ( float(cm)/sy < 0.90 ):
                lim = p
        if max_cov < x[lim]:
            max_cov = x[lim]
        if max_y < max(ny):
            max_y = max(ny)
        # plot!
        ax.plot(x, ny, color=s_color, label=round(sd_mode_cov,2))

    # configure subplot
    ax.set_title('Est. cov. distribution')
    ax.grid(True, linestyle='-', linewidth=0.3)
    ax.set_xlabel('Est. cov.')
    ax.set_ylabel('Proportion')   
    global max_percentile
    ax.legend(fontsize="xx-small", bbox_to_anchor=(0.80, 0.95), loc=2, borderaxespad=0.)
    ax.set_xlim(0,max_cov)
    ax.set_ylim(0,max_y + max_y*0.10)
    return ax

def plot_per_read_GC_content(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting GC content ]" )
    # ========================================================

    binwidth = 1.0
    for s in data:
        per_read_GC_content = {}
        s_name = s
        s_color = data[s][0]
        sd = list()
        for i in data[s][1]:
            if i != 0:
                sd.append(round(float(i),0))
        # reading json data from preqc-lr v2.0
        x, y = zip(*sorted(collections.Counter(sorted(sd)).items()))
        
        # normalize yvalues
        sy = sum(y)
        ny = list()
        i = 0
        max_y = -1000
        peak = 0
        while ( i < len(y) ):
            j = float(y[i])/float(sy)
            if ( y[i] > max_y ):
                peak = x[i]
                max_y = y[i]
            ny.append(j)
            i+=1
        
        # plot!
        ax.plot(x, ny, color=s_color, label = peak)

    # configure subplot
    ax.set_title('Per read GC content')
    ax.set_xlabel('% GC content')
    ax.set_ylabel('Proportion')
    ax.legend( prop={'size': 5}, bbox_to_anchor=(0.80, 0.95), loc=2, borderaxespad=0.)
    ax.grid(True, linestyle='-', linewidth=0.3)
    return ax

def plot_est_genome_size(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting genome size estimates ]" )
    # ========================================================

    genome_sizes = list()
    s_names = list()
    colors = list()

    # now start plotting
    for s in data:
        s_name = s
        s_color = data[s][0]
        sd = data[s][1]
        genome_size_in_megabases = round(float(sd)/float(1000000), 2)
        genome_sizes.append(genome_size_in_megabases)
        s_names.append(s_name)
        colors.append(str(s_color))

    # plotting the number of overlaps/read
    y_pos = np.arange(len(genome_sizes))
    ax.barh(y_pos, genome_sizes, align='center')
    
    # add est genome size values to the bars
    rects = ax.patches
    if len(s_names) == 1 :
        height = 0.3
    else:
        height = 1.0/float(len(s_names))
    for rect, value, s in zip(rects, genome_sizes, s_names):
        rect.set_facecolor(data[s][0])
        rect.set_height(height)
        t = ax.text(0.0, rect.get_y() + rect.get_height()/2.0, s + ": " + str(value) + "Mbp", ha='left', va='center', fontsize='8')
        t.set_bbox(dict(facecolor='#FFFFFF', alpha=0.5, edgecolor='#FFFFFF'))

    # configure subplot
    ax.set_yticks([])
    ax.set_title('Est. genome size')
    ax.set_xlabel('Genome size (Mbp)')
    ax.set_ylabel(' \n \n ')
    ax.grid(True, linestyle='-', linewidth=0.3)
    return ax

def plot_median_cov_vs_min_read_length(ax, data, s, output_prefix):
    # ========================================================
    custom_print( "[ Plotting median cov as a function of minimum read length ]" )
    # ========================================================
    
    s_name = s
    s_color = data[s][0]
    sd = data[s][1]        # dictionary: key = min read length cut off, value = median cov
    s_marker = data[s][2]
    x = list()
    y = list()
    for key, value in sorted(sd.iteritems(), key=lambda (k,v): (v,k)):
        x.append(float(key))
        y.append(float(value))

    # plot!
    ax.scatter(x, y, label=s_name, color=s_color, alpha=0.3)

    # set x limit
    global max_percentile
    x_lim = max(x)*(float(max_percentile)/100.0)

    # configure subplot
    ax.set_title('Median cov. vs min. read length \n(' + s + ')' )
    ax.grid(True, linestyle='-', linewidth=0.3)
    ax.set_xlabel('Min. read length (bps)')
    ax.set_ylabel('Median cov')
    ax.set_xlim(0, x_lim)
    return ax

def plot_total_num_bases_vs_min_read_length(ax, data, s, output_prefix):
    # ========================================================
    custom_print( "[ Plotting total number of bases as a function of minimum read length ]" )
    # ========================================================

    s_name = s
    s_color = data[s][0]
    sd = data[s][1]        # dictionary: key = min read length cut off, value = total bases
    s_marker = data[s][2]
    x = list()
    y = list()
    for key, value in sorted(sd.iteritems(), key=lambda (k,v): (v,k)):
        x.append(float(key))
        y.append(float(value))

    # let's change the total base values to gigabases
    ny = list()
    for i in y:
        ny.append(float(i)/float(1000000))
    
    # let's change the read lengths to kilobases
    nx = list()
    for j in x:
        nx.append(float(j)/float(1000))

    # plot!
    ax.plot(nx, ny, label=s_name, color=s_color)

    # set x limit
    global max_percentile
    x_lim = max(nx)*(float(max_percentile)/100.0)

    # configure subplot
    ax.set_title('Total number of bases \n(' + s + ')' )
    ax.grid(True, linestyle='-', linewidth=0.3)
    ax.set_xlabel('Min. read length (kbps)')
    ax.set_ylabel('Total num. bases (Gbps)')
    ax.set_xlim(0, x_lim)
    return ax

def plot_ngx(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting NGX values ]" )
    ax.set_title('NG(X)')
    # ========================================================

    for s in data:
        s_name = s
        s_color = data[s][0]
        sd = data[s][1]
        s_marker = data[s][2]
        lists = list()
        for key in sd:
            lists.append((int(key), sd[key]))
        lists.sort(key=lambda x: x[0])
        x, y = zip(*lists)
        ax.plot(x, y, label=s_name, color=s_color)

    # configure subplot
    ax.grid(True, linestyle='-', linewidth=0.3)
    ax.set_xlabel('X (%)')
    ax.set_ylabel('Contig length (Mbps)')
    ax.set_xlim(0,100)
    return ax

def plot_indel_error_rates(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting INDEL error rates ]" )
    # ========================================================
    for s in data:
        s_name = s
        s_color = data[s][0]
        sd = list()
        for i in data[s][1]:
            if i != 0:
                sd.append(round(i,3))
        x, y = zip(*sorted(collections.Counter(sorted(sd)).items()))

        # normalize yvalues
        sy = sum(y)
        ny = list()
        i = 0
        max_y = -1000
        while ( i < len(y) ):
            j = float(y[i])/float(sy)
            if ( y[i] > max_y ):
                max_y = y[i]
            ny.append(j)
            i+=1

        # plot!
        ax.plot(x, ny, color=s_color, label=s_name)

    # configure subplot
    ax.set_title('INDEL error rates distribution')
    ax.set_xlabel('INDEL error rate')
    ax.set_ylabel('Proportion')
    ax.grid(True, linestyle='-', linewidth=0.3)
    return ax

def plot_overlap_lengths(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting overlap lengths ]" )
    # ========================================================
    for s in data:
        s_name = s
        s_color = data[s][0]
        sd = list()
        for i in data[s][1]:
            if i != 0:
                sd.append(int(math.ceil(i / 10.0)) * 10)
        x, y = zip(*sorted(collections.Counter(sorted(sd)).items()))

        # normalize yvalues
        sy = sum(y)
        ny = list()
        i = 0
        max_y = -1000
        while ( i < len(y) ):
            j = float(y[i])/float(sy)
            if ( y[i] > max_y ):
                max_y = y[i]
            ny.append(j)
            i+=1

        # plot!
        ax.plot(x, ny, color=s_color, label=s_name)

    # configure subplot
    ax.set_title('Overlap lengths distribution')
    ax.set_xlabel('Overlap length (bps)')
    ax.set_ylabel('Proportion')
    ax.grid(True, linestyle='-', linewidth=0.3)
    return ax

def plot_dust_scores(ax, data, output_prefix):
    # ========================================================
    custom_print( "[ Plotting DUST score distribution ]" )
    # ========================================================
    for s in data:
        per_read_DUST_score = {}
        s_name = s
        s_color = data[s][0]
        sd = list()
        for i in data[s][1]:
            if i != 0:
                sd.append(float(i))
        x, y = zip(*sorted(collections.Counter(sorted(sd)).items()))

        # normalize yvalues
        sy = sum(y)
        ny = list()
        i = 0
        max_y = -1000
        while ( i < len(y) ):
            j = float(y[i])/float(sy)
            if ( y[i] > max_y ):
                max_y = y[i]
            ny.append(j)
            i+=1

        # plot!
        ax.plot(x, ny, color=s_color, label=s_name)

    # configure subplot
    ax.set_title('DUST score distribution')
    ax.set_xlabel('DUST score')
    ax.set_ylabel('Proportion')
    ax.grid(True, linestyle='-', linewidth=0.3)
    return ax


def custom_print(s):
    global verbose
    global log
    if verbose:
        print s
    log.append(s)

if __name__ == "__main__":
    main()


