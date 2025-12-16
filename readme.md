# Bruce's Soccer Tourney Poster Generator

This python script generates posters for the soccer tournaments with group and elimination rounds. It shows all the matches, with spots to fill in scores. There are places to track group stage results. And the knockout stages have places to fill in the teams as they advance.

The initial iteration created posters for the 2022 world cup. Since the team/schedule data is read from an excel sheet, posters can be generated for other tournaments. Known tournaments are xlsx files in the `database` subdirectory.

The script can generate PDFs at one paper size with cut-marks for cropping to a smaller size. This is mostly unnecessary now as most print shops (eg FedEx in the US) can print with full bleed to their standard paper sizes.

