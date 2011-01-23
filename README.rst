This program facilitates the analysis of auditory evoked responses (tested with
auditory brainstem responses and compound action potentials).  You can visualize
the waveform series collected during a single experiment, and identify the
threshold and extract the amplitude and latency of each of the individual peaks
in the waveform.  

The default input/output format used by the program are designed to work with
the in-house file format used by Eaton Peabody Laboratory.  Refer to the
peakio.py file for documentation on how to adapt this program to your data
format.

Loading Data
------------
Data can be loaded by opening a file directly via the command line ("python
analyze.py CAP-139-5"), dragging and dropping the file from the operating system
desktop, or selecting it via the file menu.  Note that you may specify multiple
files via any of these methods.  When using the command line, wildcards should
work (e.g. python analyze.py c:\\data\\AEH\\AEH350\\ABR-\*)

Program Options
---------------
Options are specified via the command line

Usage: analyze.py [options] [filenames]

Options:
  -h, --help            show this help message and exit
  --nofilter            Do not filter waveform
  --lowpass=LOWPASS     Lowpass cutoff (Hz), default 10,000 Hz
  --highpass=HIGHPASS   Highpass cutoff (Hz), default 200 Hz
  --order=ORDER         Filter order, default 1st order
  -d DIRECTORY, --directory=DIRECTORY
                        Default directory for files
  -i, --invert          Invert waveform polarity when waveforms are loaded

If you regularly use the program with a different set of default values, I
recommend you create a shortcut or alias that contains these defaults.  Under
Windows, you can create a shortcut by right-clicking on the desktop (or an
explorer window), selecting "New -> Shortcut" from the pop-up menu.  You will
get a dialog box asking to type the location of the item.  Enter the following
string:

python C:\\programs\\ABR\\analyze.py --invert --directory c:\\data

Where C:\\programs\\ABR\\analyze.py would be replaced with the appropriate path to
the program and the options would be replaced with your preferred options.

Analysis
--------
On load each waveform is bandpass filtered using a butterworth filter (filter
order and highpass and lowpass cutoffs are specified via command-line options).
This filtering process removes the baseline shift as well as high-frequency
noise that may interfere with the peak-finding algorithm.  To prevent the
waveform from being filtered, use the --nofilter option; however, be aware that
this may degrade the efficacy of the automated peak.  Important note: since the
algorithm uses a forward and reverse filter (to minimize phase shift), the
actual order is double the requested order.

baseline shift as well as high frequency noise that interferes with the peak
detection algorithm.  To minimize phase shift, a first order butterworth filter
is used to forward and reverse filter the waveform.  An initial estimate of P1-5
is computed and presented for correction.  You may navigate through the waveform
stack via the up/down arrows and select a point via the corresponding number
(1-5).  Once a point is selected (it will turn to a white square), you can move
it along the waveform using the right/left arrow keys.  

Since the algorithm relies on the location of P1-5 to compute the best possible
estimate of N1-5, you should correct the location of P1-5 before asking the
algorithm to estimate N1-5.  You may also specify threshold by navigating to the
appropriate waveform (via the up/down arrows) and hitting the "t" key.

Saving
------
The amplitude and latency of each point are saved along with the threshold of
the series. If the point is part of a subthreshold waveform, the additive
inverse of the latency is saved (i.e. when parsing the file, subthreshold data
can be recognized by negative latencies).  Amplitudes from subthreshold points can be used to estimate the noise floor if desired.

The interface
-------------

The current waveform is displayed as a thick, black line.  Once a threshold is
specified, subthreshold waveforms are indicated by a dashed line.  The selected
point is indicated by a white square.  Negativities are indicated by triangles,
positivities as squares.  Red is P1/N1, yellow is P2/N2, green is P3/N3, light
blue is P4/N4, and dark blue is P5/N5.

The following keybindings are used when analyzing a waveform series:

    Up/Down arrows
        Select previous/next waveform in the series
    Right/Left arrows
        Move a toggled peak left or right along the waveform.  Movement of the
        peak will "snap" to estimated peaks in the waveform.  To adjust the peak
        in fine increments, hold down the shift key simultaneously.
    Number keys 1-5
        Select the corresponding peak on the current waveform.  To select N1-5,
        hold down shift while pressing the corresponding number.
    I
        Estimates N1-5 for all waveforms.  If N1-5 is already estimated,
        recomputes the estimate.
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

Some keys will repeat if you hold down the key, which may be useful when
navigating through the waveforms or adjusting the location of a peak.

Code Dependencies
-----------------

    wxPython_, numpy_, scipy_, matplotlib_
    
.. _wxPython: http://www.wxpython.org/
.. _numpy: http://numpy.scipy.org/
.. _scipy: http://www.scipy.org/
.. _matplotlib: http://matplotlib.sourceforge.net/

The simplest way to satisfy these dependencies is to install `Python(x,y)`_ or the
`Enthought Python Distribution`_.

.. _`Python(x,y)`: http://www.pythonxy.com
.. _`Enthought Python Distribution`: http://www.enthought.com/products/epd.php

The Algorithm
-------------
See the documentation on find_np in peakdetect.py for an overview of how the
algorithm works.
