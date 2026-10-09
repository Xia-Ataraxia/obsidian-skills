# Videos

Identify the original video by its canonical public URL or supplied stable identity.
Retain speaker, timestamp, transcript language and each obtained segment when those were actually available.
A metadata lookup or a video link is not a transcript.
Missing subtitles, inaccessible audio and absent segments remain explicit omissions.

Use an actually obtained transcript/export; do not reconstruct words from a generated summary.
Transcripts: `defuddle "$URL"` or `yt-dlp --write-subs --write-auto-subs --skip-download "$URL"`; when both fail, say so rather than reconstructing speech.
A supplied transcript can be ingested directly without capture.
The vault owner determines whether its actual destination is a video or YouTube leaf.

Keep transcript evidence separate from analysis.
Cite timestamp spans, preserve conflicting statements and record conversion/translation separately.
No word count, transcript size or successful network response proves completeness.
