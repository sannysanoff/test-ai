
This is wideband SDR sample, it contains I/Q samples. Assume center frequency is 0, and full spectrum is in range +-192 khz.
. You must detect from 15 to 25 upper sideband transmissions (from most energy to small energy transmission) randomly spaced. 
I want you to find their removed carrier frequencies. 
Upper sideband transmission does not contain carriers.
Because voice is translated in upper sideband, vocal harmonics hint the carrier frequency.
Assiming person is saying vowel 'A', at frequency 180 hz, it will have harmonics each 180 hz, i.e. 180, 360, 540 etc. 
If removed carrier offset within wideband is -120000 hz, then frequencies will be visible on wideband ad -120000+180, -120000+360 and -120000+540hz, and more harmonics toward higher frequencies.
Next moment, tone will go up, and frequencies are 190,380, 570 etc.
Assuming also, radio operator is using low-cut (high-pass) filter that cuts away lower 300 hz of voice. Then, only 2nd harmonics will be visible on the waterfall spectrogram: 
in first case, 360, 540, .... anmd in second case 380, 570, .... 
if they are translated to -120000 hz (we don't know this value), we'll get -119640,-119460,.... and -119629,-119430 at second time point.
It's possible to find common frequency by extending this arithmetic progression to the left, so -120000 will be missing 0th harmonic.

In the sample above, as I said, there's from 15 to 25 transmissions. They have certain duration, so many vowels like that, hinting at the removed carrier.

I want a program that reads this WAV (it's 384 kilo samples per second), plots spectrogram, and for the duration of this sample, detects and plots marks (with different color) on spectrogram,
vertical lines of different color, identifying the most probable base frequencies of each of USB transmissions. Also, program must print in text these frequencies
with some markers: 1) signal snr 2) quality of detection (probability of proper signal) etc.

As a hint, there should not be more than 25 transmissions in this sample.
As a hint, there are strong transmission around frequencies: 4600 , 29900, 47600, 37700
All transmission are around 2200-3000 hz wide. There could be overlapping transmissions, no need to solve them.

Program must be located in root directory. Any programming language is ok, if it is performant enough.
