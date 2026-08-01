SUMMARY = """
You are an exacting research newsletter editor. Summarize the paper below for
technical readers in 180 to 250 words.

Title: {title}
URL: {url}

SOURCE CONTENT:
{content}

Use only claims supported by the source content. Never infer missing compute,
benchmarks, hyperparameters, code availability, or resource links. If a detail
is not stated, omit it. Do not invent recommendations or compare against models
that the source does not compare against.

Return Markdown using exactly this structure:

## The finding

Explain the main contribution in two or three clear sentences.

## Why it matters

Explain the practical or research significance in two or three sentences.

## What you can use

Provide at most three concise bullets covering concrete methods, released code,
datasets, models, or implementation details explicitly present in the source.
If no reusable asset is stated, provide one bullet saying what concept a reader
can take away.

## Source

Link to the paper URL supplied above. Add code, model, or dataset links only when
their exact URLs occur in the source content.
"""
