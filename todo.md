## now

- take results from spreadsheet and print them instead of boxes/forms.
- command line with argparse.
- lists of pages from database (or ?).

## future

- layout engine
	- move most `CBlot.__init__` stuff into `Layout`/`Draw` phases.
	- remove `s_dY` and its ilk. everything resizable.
	- `SVector` (perhaps `SSize`?). dataclass of `dX`/`dY` floats.
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
- tourney properties.
- don't rely on excel tables, just use worksheets.
- use babel for date time formats.
- localized text from database.
- get **ALL** text from spreadsheet.
- more localization
	- split non-tourney strings into their own db next to fonts.
	- font choices in this non-tourney db.
- print against 2018 data.
