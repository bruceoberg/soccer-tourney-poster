## now

- tourney properties.
- print against 2018 data.
	- get **ALL** text from spreadsheet.

## future

- command line with argparse.
- lists of pages from database (or ?).
- font choices from database.
- localized text from database.
- layout engine
	- move most `CBlot.__init__` stuff into `Layout`/`Draw` phases.
	- remove `s_dY` and its ilk. everything resizable.
	- `SVector` (perhaps `SSize`?)
    - `SRect`
		- `Adjacent()`, `RectSplit()`, `LRectSplit()`
		- remove `SRect.Copy()` and replace with `RectFoo()` static
	- `CBlotSet`
		- `CGridBlot`
		- `CLayoutBlot`
			- `CCol` / `CRow`
- monochrome
- fix FPDF2 to generate embedded fonts that illustrator can recognize.

## never

- check boxes in group stats

## done

- elimination match numbers not bold.
- page knows about timezone.
- bracket layout of elimination matches.
- stage titles.
- no borders.
- no match numbers.
- grey elimination borders.
- group name hints on group matches.
- point/goal spots in group stats.
- minimal readme.
