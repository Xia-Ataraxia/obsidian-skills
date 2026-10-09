# Videos

Identify the original video by its canonical public URL or supplied stable identity.
Retain speaker, timestamp, transcript language and each obtained segment when those were actually available.
A metadata lookup or a video link is not a transcript.
Missing subtitles, inaccessible audio and absent segments remain explicit omissions.

Use an actually obtained transcript/export; do not reconstruct words from a generated summary.
For YouTube, run `defuddle parse "$URL" --md -l <code>` first, with the video's spoken language as `<code>`; when the language is not known, a first call with `-j` reports it along with title, description, channel and published date. Without `-l` the track may be an auto-translation, so check that the returned text is in that language.
`yt-dlp --write-subs --write-auto-subs --skip-download "$URL"` is the fallback only when defuddle fails or returns no transcript; when both fail, say so rather than reconstructing speech.
The canonical URL is the original, so no caption file is kept as an attachment; write the `yt-dlp` fallback's files to a temporary directory.
Record in Ingest Notes which tool and which caption track (manual or auto-generated) was used, since auto captions misrecognize names.
Preserve chapter headings and timestamps as obtained.
A highlight reel at the start or a trailer for another programme at the end stays in Raw, is named with its timestamp span in Ingest Notes, and is not separate evidence.
A supplied transcript can be ingested directly without capture.
The vault owner determines whether its actual destination is a video or YouTube leaf.

Keep transcript evidence separate from analysis.
Cite timestamp spans, preserve conflicting statements and record conversion/translation separately.
No word count, transcript size or successful network response proves completeness.
