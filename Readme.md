# SV Docs to Transkribus

This repo contains the code for a two-step process:

1. ```doc_scraper.py```
	1. pulls basic document and page-level data from the voyages api
	1. saves this into a file ```documents_pages.json```
1. ```transkribus_pusher.py```
	1. parses the ```documents_pages.json``` file
	1. for each document, it then
		1. creates an upload job in Transkribus
		1. for each page in that document, it then
			1. downloads the full-sized jpeg pointed at in the json file
			1. saves it as {{primary_key}}.jpg
			1. pushes the jpg up to the transkribus server
		
It was taking a long time, so I built in multithreading. Within each document, the pages are uploaded in parallel -- but the documents are handled serially.

*You need a credentials.py file to access both transkribus and the sv api*

## Why?

Transkribus was failing on the large TIF's from the libraries affiliated with the South Seas project.

So we had to push up our JPEG collections in order to run HTR on these.

However, the best source for those JPEG's was still the libraries' IIIF endpoints. We have these pointers in our database, but were only holding the large TIF's locally.

## Use examples:

### Getting the image metadata from the SV API

### Pushing the files up

This use iterates over all documents in the json file, and uploads the pages on a single-threaded process.

	python transkribus_pusher.py

This use specifies a single document, and a number of worker processes

	python transkribus_pusher.py --shortref="DOCP Huntington 57 17" --workers=5