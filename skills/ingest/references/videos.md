# Videos

Identify the original video by its canonical public URL or supplied stable identity.
Retain speaker, timestamp, transcript language and each obtained segment when those were actually available.
A metadata lookup or a video link is not a transcript.
Missing subtitles, inaccessible audio and absent segments remain explicit omissions.

Use an actually obtained transcript/export; do not reconstruct words from a generated summary.
The local [transcript extractor](../scripts/youtube-transcript-extract.py) runs as `python3 scripts/youtube-transcript-extract.py "$URL_OR_ID" -o "$TRANSCRIPT" --metadata-output "$EVIDENCE" --timeout 60` on explicitly authorized source and output paths.
It tries the local `defuddle` CLI, then three public Defuddle gateway URLs, and obtains diagnostic metadata through YouTube oEmbed and optional `yt-dlp`.
It accepts only readable text in a bounded `## Transcript` section, retaining the obtained Markdown without fabricating missing speech.
Exit 0 writes the transcript and reports readback-ready output paths; exit 1 reports missing/challenge/error evidence without writing a fabricated transcript, and invalid source IDs exit 2.
Keep its metadata JSON, extraction method and original Markdown; inspect the actual written bytes before handing that artifact to direct ingest.
The extractor does not authenticate vault approval or enforce destination policy. Missing binaries/network results are explicit diagnostics, and `completeness` remains `unknown`.
The source files are present under local transfer authorization, not a confirmed origin redistribution grant.
A supplied transcript can be ingested directly without capture or that helper.
The vault owner determines whether its actual destination is a video or YouTube leaf.

Keep transcript evidence separate from analysis.
Cite timestamp spans, preserve conflicting statements and record conversion/translation separately.
No word count, transcript size or successful network response proves completeness.
