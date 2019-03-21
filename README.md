# ABR analysis

This program facilitates the analysis of auditory evoked responses (tested with auditory brainstem responses and compound action potentials).  You can visualize the waveform series collected during a single experiment, and identify the threshold and extract the amplitude and latency of each of the individual peaks in the waveform.

The default input/output format used by the program are designed to work with the in-house file format used by Eaton Peabody Laboratory.  Refer to the parsers directory for documentation on how to adapt this program to your data format.

## Programs available

There are two main interfaces to the ABR analysis program. The first is the basic interface where you manually drag files from your file browser and drop them on the window. You can drag one file or multiple files. Each file will be opened in a separate tab. The second interface is an automatic one that will loop through all unprocessed ABR files found in a folder and present each file to you individually for analysis. Once you save the analysis, it will immediately move to the next file.

Both interfaces are accessed via the launcher. When you first open the launcher, you will specify:

* Your name (i.e., the "analyzer")
* The file format.  For many of you, you will pick the EPL CFTS unless you are using my software, [psiexperiment](https://github.com/bburan/psiexperiment) for data acquisition.
* Which waves you want to analyze. If none are checked, we will assume that you only wish to mark threshold.
* Filter settings to use. The original version of this program (distributed via the EPL website), filters waveforms using a 300 to 3000 Hz bandpass butterworth filter. However, many 

## Processing

Each waveform is bandpass filtered using a butterworth filter (filter order and highpass and lowpass cutoffs are specified via command-line options). This filtering process removes the baseline shift as well as high-frequency noise that may interfere with the peak-finding algorithm.  To prevent the waveform from being filtered, use the --nofilter option; however, be aware that this may degrade the efficacy of the automated peak.  Important note: since the algorithm uses a forward and reverse filter (to minimize phase shift), the actual order is double the requested order.

An initial estimate of P1-5 is computed and presented for correction.  You may navigate through the waveform stack via the up/down arrows and select a point via the corresponding number (1-5).  Once a point is selected (it will turn to a white square), you can move it along the waveform using the right/left arrow keys.  Since the algorithm relies on the location of P1-5 to compute the best possible estimate of N1-5, you should correct the location of P1-5 before asking the algorithm to estimate N1-5.  You may also specify threshold by navigating to the appropriate waveform (via the up/down arrows) and hitting the "t" key.

## Output format

The amplitude and latency of each point are saved along with the threshold of the series. If the point is part of a subthreshold waveform, the additive inverse of the latency is saved (i.e. when parsing the file, subthreshold data can be recognized by negative latencies).  Amplitudes from subthreshold points can be used to estimate the noise floor if desired.

## Interface

The current waveform is displayed as a thick, black line.  Once a threshold is specified, subthreshold waveforms are indicated by a dashed line.  The selected point is indicated by a white square.  Negativities are indicated by triangles, positivities as squares.  Red is P1/N1, yellow is P2/N2, green is P3/N3, light blue is P4/N4, and dark blue is P5/N5.

The following keys can be used when analyzing a waveform:

    Up/Down arrows
        Select previous/next waveform in the series
    Right/Left arrows
        Move a toggled peak left or right along the waveform.  Movement of the
        peak will "snap" to estimated peaks in the waveform.  To adjust the peak
        in fine increments, hold down the alt key simultaneously.
    Number keys 1-5
        Select the corresponding peak on the current waveform.  To select N1-5,
        hold down alt while pressing the corresponding number.
    I
        Estimates P1-5 for all waveforms on the first press. N1-5 for all
        waveforms on the second press. After that, nothing happens.
    U
        Updates guess for corresponding P or N of successive waveforms based on
        position of currently toggled P or N.
    N
        Toggles normalized view of waveform.
    +/- keys
        Increases/decreases scaling factor of waveform.
    S
        Saves amplitude and latency of peaks.
    T
        Set threshold to current waveform.
    Alt+Up
        Indicate that all waveforms are below threshold.
    Alt+Down
        Indicate that all waveforms are above threshold.

Some keys will repeat if you hold down the key, which may be useful when navigating through the waveforms or adjusting the location of a peak.
