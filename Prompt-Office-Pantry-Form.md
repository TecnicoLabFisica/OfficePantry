---
tags: [office-pantry, prompt, setup]
date: 2026-09-06
status: ready-to-run
---

# 🥨 Office Pantry — Gemini prompt for the suggestion form

The suggestions page needs a Google Form and a published response sheet. Building them
by hand is a click-through, and it is quietly precision work: `assets/pantry.js` does not
validate the form, it pattern-matches the CSV column headers. One reworded question or
one decorated category option and the list renders blanks with no error.

So the prompt below does not say «make a suggestions form». It pins every string the
page depends on and gives the reason for each, because a reason is what stops a model
from improving `Product` into something friendlier.

Paste it whole into Gemini. What comes back is a Google Apps Script you run once.

Related: [[Status-Office-Pantry]] · [[Plan-Office-Pantry]]

---

## The prompt

```text
You are writing a Google Apps Script for a small office snack fund called Office
Pantry. It is a static GitHub Pages site that reads a Google Form's published
response CSV and renders the suggestions on a page. There is no server.

Write ONE complete, standalone Apps Script that I will paste into a new project at
script.google.com and run once. It must create the suggestion form and its linked
response spreadsheet.

## The contract

The page does not validate the form. It matches the CSV column headers by substring
and looks the category value up in a config file. Every string below is load-bearing,
and getting one wrong makes suggestions silently render blank rather than error. Do
not adjust any of them for style.

1. The first question is a required short-answer question titled exactly: Product
   Why: the page finds the column with header.toLowerCase().includes('product'), and
   when that fails it falls back to column B. Timestamp is column A, so Product must
   be the first question either way.

2. The second question is a required multiple-choice question titled exactly: Category
   Why: matched with header.toLowerCase().includes('categor').

3. Its choices are exactly these five, in this order, as plain text:
   Snacks, Drinks, Coffee, Supplements, Other
   Why: the page lowercases the submitted value and uses it as a key into a config
   file that supplies the emoji and label. "🍪 Snacks" misses the key and renders raw.
   No emoji, no punctuation, no rewording.

4. "Other" is a normal choice. Do NOT enable Google's free-text "Other" option
   (showOtherOption). Why: it lets a respondent write anything, and anything that is
   not one of the five keys has no category to match.

5. Email collection is OFF: setCollectEmail(false). If that method is unavailable in
   the current runtime, use
   setEmailCollectionType(FormApp.EmailCollectionType.DO_NOT_COLLECT) instead.
   Why: the response sheet gets published to the web. Every column in it becomes
   readable by anyone with the URL. The whole project is first-names-only for the
   same reason.

6. No sign-in and no one-response-per-user: setRequireLogin(false) and
   setLimitOneResponsePerUser(false).
   Why: "no account, no password, no app" is the design goal. Anyone should be able
   to scan the sticker and suggest something.

7. Response editing is OFF: setAllowResponseEdits(false).
   Why: an edited response silently rewrites a row that was already published. In
   this project corrections are always new entries, never edits to old ones.

8. Exactly two questions. Do not add a name field, a comment field, a priority
   field or anything else. Why: the page renders only product and category, so any
   other column would be collected and published in a world-readable CSV, and never
   shown to anyone.

## What the script must do

Put these at the top as editable constants: FUND_NAME ("Office Pantry"),
ADMIN_EMAIL, FORM_TITLE, SHEET_TITLE, and the CATEGORIES array.

1. Refuse to run twice. If a Drive file named FORM_TITLE already exists, log a clear
   message and return without creating anything, so a second run cannot orphan the
   first form.
2. Create the form with FormApp.create, set a one-line description telling coworkers
   the admin sees every suggestion.
3. Add the two questions above, in order, both required.
4. Apply all four settings from points 5-7 of the contract.
5. Create a spreadsheet named SHEET_TITLE and attach it with
   form.setDestination(FormApp.DestinationType.SPREADSHEET, ...). Then call
   SpreadsheetApp.flush() and re-open the spreadsheet by id to get the response
   sheet, which only exists after the destination is set. Find it by the sheet whose
   name starts with "Form Responses", falling back to the last sheet.
6. Install an installable onFormSubmit trigger, bound to the form, that emails
   ADMIN_EMAIL the product and category of each new response. Before creating it,
   loop over ScriptApp.getProjectTriggers() and delete any existing trigger with the
   same handler function name, so re-running never stacks duplicates. Read the values
   from e.response.getItemResponses(). Google Forms' own "Get email notifications for
   new responses" toggle has no Apps Script API, which is why this trigger exists;
   mention the manual toggle as an alternative in a comment.
7. Finish by Logger.log-ing a labelled block containing:
   - the form's embed URL: form.getPublishedUrl() with "?embedded=true" appended
   - the form's edit URL
   - the spreadsheet URL
   - the response sheet's getSheetId(), labelled as the gid needed for the published
     CSV URL

## Output

Return the complete script in one code block, then a short numbered list of what I do
after running it. No introduction, no explanation of what Apps Script is, no
alternative versions. Use plain JavaScript, no libraries. Comment only where the
reason is not obvious from the code.
```

---

## After the script runs

The script does everything except the one step Apps Script has no API for.

### 1. Publish the response sheet

Open the spreadsheet → **File → Share → Publish to web** → select **Form Responses 1**
→ format **CSV** → *Publish* → copy the URL.

> [!warning] The published URL cannot be built from anything the script logged.
> It uses a separate published id (`/d/e/2PACX-…`), not the file id. Copy it by hand.

### 2. Fill in `data/config.json`

```json
"suggestionFormUrl": "https://docs.google.com/forms/d/e/.../viewform?embedded=true",
"suggestionSheetCsvUrl": "https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=0&single=true&output=csv"
```

Then `python tools/doctor.py` — it warns while either key is empty, so both warnings
disappearing is the confirmation.

### 3. Check it end to end

```bash
curl -s "<the published CSV url>" | head -1     # expect: Timestamp,Product,Category
python -m http.server 8000                      # then open /suggestions.html
```

Submit one test suggestion and confirm three things: the notification email arrives, the
row appears in the sheet, and the page lists it **with its category emoji** rather than
the raw word. Raw text means the option spelling and the `categories` keys in
`data/config.json` have drifted apart.

Delete the test row before the sticker goes on the wall.
