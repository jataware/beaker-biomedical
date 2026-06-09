# cdapython man pages (verbatim upstream)

Source: CancerDataAggregator CDA-HelpDesk docs — documentation/cdapython/man_pages/.
Preserved verbatim so the skill is self-contained. The synthesized, cross-referenced
version lives in references/FUNCTIONS.md.


---

---
title: tables()
---

Get a list of all searchable CDA data tables.

`tables()`
    
    
## Returns

list of strings: names of searchable CDA tables.

---

---
title: columns()
---

Get structured metadata describing searchable CDA columns.


`columns(*, return_data_as='', output_file='', sort_by='', debug=False, **filter_arguments)`

## Arguments

### return_data_as 
( string; optional: 'dataframe' or 'list' or 'tsv' ):
Specify how columns() should return results: as a pandas DataFrame,
a Python list, or as output written to a TSV file named by the user.
If this argument is omitted, columns() will default to returning
results as a DataFrame.

### output_file
( string; optional ):
If return_data_as='tsv' is specified, output_file should contain a
resolvable path to a file into which columns() will write
tab-delimited results.

### sort_by
( string or list of strings; optional:
any combination of 'table', 'column', 'data_type',
and/or 'nullable'):
Specify the column metadata field(s) on which to sort result data.
Results will be sorted first by the first named field; groups of
records sharing the same value in the first field will then be
sub-sorted by the second field, and so on.

Any field with a suffix of ':desc' appended to it will be sorted
in reverse order; adding ':asc' will ensure ascending sort order.
Example: sort_by=[ 'table', 'nullable:desc', 'column:asc' ]

### debug
( boolean; optional ):
If set to True, print internal process details to the standard
error stream.

## Filter arguments
### table
( string or list of strings; optional ):
Restrict returned data to columns from tables whose names match any
of the given strings. A wildcard (asterisk) at either end (or both
ends) of each string will allow partial matches. Case will be
ignored.

### column
( string or list of strings; optional ):
Restrict returned data to columns whose name matches any of the
given strings. A wildcard (asterisk) at either end (or both ends)
of each string will allow partial matches. Case will be ignored.

### data_type
( string or list of strings; optional ):
Restrict returned data to columns whose data type matches any of
the given strings. A wildcard (asterisk) at either end (or both
ends) of each string will allow partial matches. Case will be
ignored.

### nullable
( boolean; optional ):
If set to True, restrict returned data to columns whose values are
allowed to be empty; if False, return data only for columns
requiring nonempty values.

### description
( string or list of strings; optional ):
Restrict returned data to columns whose `description` field matches
any of the given strings. Wildcards will be automatically applied
(end-to-end matching makes no sense here), emphasized by the name
'description_contains' and not 'description'. Case will be ignored.

### exclude_table
( string or list of strings; optional ):
Restrict returned data to columns from tables whose names do _not_
match any of the given strings. A wildcard (asterisk) at either end
(or both ends) of each string will allow partial matches. Case will
be ignored.

## Returns
pandas.DataFrame where each row is a metadata record describing one
searchable CDA column comprising the following fields:

`table` (string: name of the CDA table containing this column)
`column` (string: name of this column)
`data_type` (string: data type of this column)
`nullable` (boolean: if True, this column can contain null values)
`description` (string: prose description of this column)

OR 

list of column names

OR 

returns nothing, but writes results to a user-specified TSV file


---

---
title: column_values()
---

Show all distinct values present in `column`, along with a count
of occurrences for each value.

```
column_values
(column='', *, return_data_as='dataframe', output_file='', sort_by='', filters='', data_source='', force=False, debug=False)
```


## Arguments

### column
( string; required ):
The column to fetch values from.

### return_data_as
( string; optional:'dataframe'(default) or 'list' or 'tsv' ):
Specify how `column_values()` should return results: as a pandas
DataFrame, a Python list, or as output written to a TSV file named
by the user. If this argument is omitted, column_values() will default
to returning results as a DataFrame.

### output_file
( string; optional ):
If return_data_as='tsv' is specified, output_file should contain a
resolvable path to a file into which column_values will write tab-delimited results.

### sort_by
( string; optional:'count'( default for `return_data_as='dataframe'` and `return_data_as='tsv'` ) or 'value'( default for `return_data_as='list'` ) or '`count:desc`' or '`value:desc`' or '`count:asc`' or '`value:asc`' ):

Specify the primary column to sort when preparing result data: on
values, or on counts of values.

A column name with a suffix of '`:desc`' appended to it will be
sorted in reverse order; adding '`:asc`' will ensure ascending sort
order. Example: `sort_by='value:desc'`

Secondary sort order is automatic: if the results are to be
primarily sorted by count, then the automatic behavior will be to
also (alphabetically) sort by value within each group of values
that all share the same count. If results are primarily sorted by
value, then there is no secondary sort -- each value is unique by
design, so results don't contain groups with the same value but
different counts, so there's nothing to arrange once the primary
sort has been applied.

### filters

( string or list of strings; optional ):

Restrict returned values to those matching any of the given strings.
A wildcard (asterisk) at either end (or both ends) of each string
will allow partial matches. Case will be ignored. Use an empty
filter string '' to match and count missing (null) values.

### data_source

( string; optional ):
Restrict returned values to the given upstream data source, such
as 'GDC', 'PDC', 'IDC', 'GC' and 'ICDC'. Defaults to `''` (no filter).

### force
( boolean; optional ): 
Force execution of high-overhead queries on columns (like IDs)
flagged as having large numbers of values. Defaults to False, in which case attempts to retrieve values for flagged columns will result in a warning.

## Returns
pandas.DataFrame 

OR

list

OR

returns nothing, but writes retrieved data to a user-specified TSV file


---

---
title: summarize_subjects()
---

For a set of CDA subject rows that all match a user-specified set of filters -- "result rows" -- get a report showing counts of values present in that
set of rows, profiled across (user-modifiable) columns of interest.

```
summarize_subjects(
    *search_terms,
    match_all=None,
    match_any=None,
    match_from_file={'input_file': '', 'input_column': '', 'cda_column_to_match': ''},
    data_source=None,
    add_columns=None,
    exclude_columns=None,
    return_data_as='',
    output_file=''
)
```


## Arguments

### search_terms
( zero or more strings; optional: ):
One or more search terms (including phrases), all of which must be
associated with each result row. Users can add a wildcard character * to
either or both ends of each search term to enable partial matches
to longer values. Example:
    summarize_files( 'kidney', 'adeno*', 'latino' )
    
### match_all
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
ALL of which must be met by all result rows.

### match_any
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
AT LEAST ONE of which must be met by all result rows.

### match_from_file
( 3-element dictionary of strings; optional ):
A dictionary containing 3 named elements:
    1. 'input_file': The name of a (local) TSV file (with column names in its first row)
    2. 'input_column': The name of a column in that TSV
    3. 'cda_column_to_match': The name of a CDA column
Restrict result rows to those where the value of the given CDA
column matches at least one value from the given column
in the given TSV file.

### data_source
( string or list of strings; optional ):
Restrict results to those deriving from the given upstream data source(s). Current valid values are 'GDC', 'IDC', 'PDC',
'GC' and 'ICDC'. (Default: no filter.)

### add_columns
( string or list of strings; optional ):
One or more columns from a second table to add to summary output.

### exclude_columns
( string or list of strings; optional ):
One or more columns to remove from summary output.

### return_data_as
( string; optional: 'dataframe_list' or 'dict' or 'json' ):
Specify how to return results: as a list of pandas DataFrames, as a
Python dictionary, or as output written to a JSON file named by the user.
If this argument is omitted, then for each DataFrame that would have
been returned by the 'dataframe_list' option, a table will be
pretty-printed to the standard output stream (and nothing will be returned).

### output_file
( string; optional ):
If return_data_as='json' is specified, output_file should contain a
resolvable path to a file into which summary_counts() will write
JSON-formatted results.

## Filter strings
Filter strings are expressions of the form "COLUMN_NAME OP VALUE"
(note in particular that the whitespace surrounding OP is required),
where

- COLUMN_NAME is a searchable CDA column (see the columns() function
for details)

- OP is one of: `< <=  > >= = !=`

- VALUE is a particular value of whatever data type is stored
in COLUMN_NAME (see the columns() function for details), or
the special keyword NULL, indicating the filter should match
missing (null) values in COLUMN_NAME.

Operators `=` and `!=` will work on numeric, boolean and string VALUEs.

Operators `< <= > >=` will only work on numeric VALUEs.

Users can require partial matches to string VALUEs by adding `*` to either or
both ends. For example:

`primary_disease_type = *duct*`
`sex = F*`
`size < 100`

String VALUEs need not be quoted inside of filter strings. For example, to include
the filters specified just above in the `match_all` argument, we can write:

`summarize_subjects( match_all=[ 'primary_disease_type = *duct*', 'sex = F*' ] )`

NULL is a special VALUE which can be used to match missing data. For
example, to get a count summary for rows where the `sex` field is missing data,
we can write:

`summarize_subjects( match_all=[ 'year_of_birth = NULL' ] )`

## Returns
        
list of pandas DataFrames, with one DataFrame for each summarized column,
enumerating counts (or statistically summarizing unbounded numeric values) over all of that column's data values appearing in any CDA subject rows that match the user-specified filter criteria (the 'result rows'). Two DataFrames in this list --
    'number_of_matching_subjects' and 'number_of_files_related_to_matching_subjects' --
will contain integers representing the total number of result subject rows and the
total number of related files, respectively. Every other DataFrame in the list
will be titled with a CDA column name and will contain value counts or statistical summaries for that column as filtered by the result row set.

OR

Python dictionary enumerating counts of all data values for each summarized column (or a statistical summary of those data values, in the case of unbounded numeric data) across all CDA subject rows that match the user-specified filter criteria (the 'result rows').
Two summary keys in this dictionary -- 
    'number_of_matching_subjects' and
    'number_of_files_related_to_matching_subjects' -- 
will point to integers representing the total number of result subject rows 
and the total number of associated file rows, respectively. Every other key 
in the dictionary will contain a CDA column name; every dictionary value 
will itself be a dictionary either enumerating observed counts of all values 
appearing in that column as filtered by the result row set, or encoding a
statistical summary of those values in the case of unbounded numeric data.

OR

JSON-formatted text representing the same structure as the `return_data_as='dict'` option, written to `output_file`.

OR 

returns nothing, but displays a series of tables to standard output
describing the same data returned by the other `return_data_as` options.

And yes, we know how those first two paragraphs look. We apologize to the entire English language

---

---
title: summarize_files()
---

For a set of CDA file rows that all match a user-specified set of filters -- "result rows" -- get a report showing counts of values present in that
set of rows, profiled across (user-modifiable) columns of interest.

```
summarize_files(
    *search_terms,
    match_all=None,
    match_any=None,
    match_from_file={'input_file': '', 'input_column': '', 'cda_column_to_match': ''},
    data_source=None,
    add_columns=None,
    exclude_columns=None,
    return_data_as='',
    output_file=''
)
```


## Arguments

### search_terms
( zero or more strings; optional: ):
One or more search terms (including phrases), all of which must be
associated with each result row. Users can add a wildcard character * to
either or both ends of each search term to enable partial matches
to longer values. Example:
    summarize_files( 'kidney', 'adeno*', 'latino' )

### match_all
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
ALL of which must be met by all result rows.

### match_any
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
AT LEAST ONE of which must be met by all result rows.

### match_from_file
( 3-element dictionary of strings; optional ):
A dictionary containing 3 named elements:
    1. 'input_file': The name of a (local) TSV file (with column names in its first row)
    2. 'input_column': The name of a column in that TSV
    3. 'cda_column_to_match': The name of a CDA column
Restrict result rows to those where the value of the given CDA
column matches at least one value from the given column
in the given TSV file.

### data_source
( string or list of strings; optional ):
Restrict results to those deriving from the given upstream data source(s). Current valid values are 'GDC', 'IDC', 'PDC',
'GC' and 'ICDC'. (Default: no filter.)

### add_columns
( string or list of strings; optional ):
One or more columns from a second table to add to summary output.

### exclude_columns
( string or list of strings; optional ):
One or more columns to remove from summary output.

### return_data_as
( string; optional: 'dataframe_list' or 'dict' or 'json' ):
Specify how to return results: as a list of pandas DataFrames, as a
Python dictionary, or as output written to a JSON file named by the user.
If this argument is omitted, then for each DataFrame that would have
been returned by the 'dataframe_list' option, a table will be
pretty-printed to the standard output stream (and nothing will be returned).

### output_file
( string; optional ):
If return_data_as='json' is specified, output_file should contain a
resolvable path to a file into which summary_counts() will write
JSON-formatted results.

## Filter strings
Filter strings are expressions of the form "COLUMN_NAME OP VALUE"
(note in particular that the whitespace surrounding OP is required),
where

- COLUMN_NAME is a searchable CDA column (see the columns() function
for details)

- OP is one of: `< <=  > >= = !=`

- VALUE is a particular value of whatever data type is stored
in COLUMN_NAME (see the columns() function for details), or
the special keyword NULL, indicating the filter should match
missing (null) values in COLUMN_NAME.

Operators `=` and `!=` will work on numeric, boolean and string VALUEs.

Operators `< <= > >=` will only work on numeric VALUEs.

Users can require partial matches to string VALUEs by adding `*` to either or
both ends. For example:

`primary_disease_type = *duct*`
`sex = F*`
`size < 100`

String VALUEs need not be quoted inside of filter strings. For example, to include
the filters specified just above in the `match_all` argument, we can write:

`summarize_files( match_all=[ 'primary_disease_type = *duct*', 'sex = F*' ] )`

NULL is a special VALUE which can be used to match missing data. For
example, to get a count summary for rows where the `sex` field is missing data,
we can write:

`summarize_files( match_all=[ 'year_of_birth = NULL' ] )`

## Returns
        
list of pandas DataFrames, with one DataFrame for each summarized column,
enumerating counts (or statistically summarizing unbounded numeric values) over all of that column's data values appearing in any CDA file rows that match the user-specified filter criteria (the 'result rows'). Two DataFrames in this list --
    'number_of_matching_files' and 'number_of_subjects_related_to_matching_files' --
will contain integers representing the total number of result subject rows and the
total number of related files, respectively. Every other DataFrame in the list
will be titled with a CDA column name and will contain value counts or statistical summaries for that column as filtered by the result row set.

OR

Python dictionary enumerating counts of all data values for each summarized column (or a statistical summary of those data values, in the case of unbounded numeric data) across all CDA file rows that match the user-specified filter criteria (the 'result rows').
Two summary keys in this dictionary -- 
    'number_of_matching_files' and
    'number_of_files_related_to_matching_subjects' -- 
will point to integers representing the total number of result file rows 
and the total number of associated file rows, respectively. Every other key 
in the dictionary will contain a CDA column name; every dictionary value 
will itself be a dictionary either enumerating observed counts of all values 
appearing in that column as filtered by the result row set, or encoding a
statistical summary of those values in the case of unbounded numeric data.

OR

JSON-formatted text representing the same structure as the `return_data_as='dict'` option, written to `output_file`.

OR 

returns nothing, but displays a series of tables to standard output
describing the same data returned by the other `return_data_as` options.

And yes, we know how those first two paragraphs look. We apologize to the entire English language

---

---
title: get_subject_data()
---

Get CDA subject rows ('result rows') that match user-specified criteria.


```
get_subject_data(
    *search_terms,
    match_all=None,
    match_any=None,
    match_from_file={'input_file': '', 'input_column': '', 'cda_column_to_match': ''},
    data_source=None,
    add_columns=None,
    exclude_columns=None,
    collate_results=False,
    include_external_refs=False,
    return_data_as='dataframe',
    output_file=''
)
```

## Arguments

### search_terms
( zero or more strings; optional: ):
One or more search terms (including phrases), all of which must be
associated with each result row. Users can add a wildcard character * to
either or both ends of each search term to enable partial matches
to longer values. Example:
    get_subject_data( 'kidney', 'adeno*', 'latino' )

### match_all 
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
ALL of which must be met by all result rows.

### match_any 
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
AT LEAST ONE of which must be met by all result rows.

### match_from_file 
( 3-element dictionary of strings; optional ):
A dictionary containing 3 named elements:
    1. 'input_file': The name of a (local) TSV file (with column names in its first row)
    2. 'input_column': The name of a column in that TSV
    3. 'cda_column_to_match': The name of a CDA column
Restrict result rows to those where the value of the given CDA
column matches at least one value from the given column
in the given TSV file.

### data_source 
( string or list of strings; optional ):
Restrict results to those deriving from the given upstream
data source(s). Current valid values are 'GDC', 'IDC', 'PDC',
'GC' and 'ICDC'. (Default: no filter.)

### add_columns 
( string or list of strings; optional ):
One or more columns from a second table to add to result data.

### exclude_columns 
( string or list of strings; optional ):
One or more columns to remove from result data.

### collate_results
( boolean; optional ):
If True: for each result subject, include a DataFrame collating
results linked to that subject from each non-subject table that was
queried. Otherwise, for each result subject, include a list of
unique values associated with that subject from each non-subject
column that was queried. Defaults to False.

### include_external_refs
( boolean; optional ):
If True: for each result subject, include a DataFrame called
'external_reference_data' that collates references to external
resources containing data describing that subject. Defaults to False.

### return_data_as
( string; optional: 'dataframe' or 'tsv' ):
Specify how to return results: as a pandas DataFrame,
or as output written to a TSV file named by the user. If this
argument is omitted, the default is to return results as a DataFrame.
    
### output_file
( string; optional ):
 If return_data_as='tsv' is specified, `output_file` should contain a
resolvable path to a file into which tab-delimited results will be
written.

## Filter strings
Filter strings are expressions of the form "COLUMN_NAME OP VALUE"
(note in particular that the whitespace surrounding OP is required),
where

- COLUMN_NAME is a searchable CDA column (see the columns() function
for details)

- OP is one of: `< <=  > >= = !=`

- VALUE is a particular value of whatever data type is stored
in COLUMN_NAME (see the columns() function for details), or
the special keyword NULL, indicating the filter should match
missing (null) values in COLUMN_NAME.

Operators `=` and `!=` will work on numeric, boolean and string VALUEs.

Operators `< <= > >=` will only work on numeric VALUEs.

Users can require partial matches to string VALUEs by adding `*` to either or
both ends. For example:

`diagnosis = *duct*`

`sex = F*`

String VALUEs need not be quoted inside of filter strings. For example, to include
the filters specified just above in the `match_all` argument, when querying
the `subject` table, we can write:

`get_subject_data( match_all=[ 'diagnosis = *duct*', 'sex = F*' ] )`

NULL is a special VALUE which can be used to match missing data. For
example, to get CDA subject data for which the `cause_of_death` field
is missing data, we can write:

`get_subject_data( match_all=[ 'cause_of_death = NULL' ] )`

## Returns
(Default) A pandas.DataFrame containing CDA subject data matching the user-specified filter criteria. The DataFrame's named columns will match columns in the `subject` table plus any optional user-added columns from other tables, and each row in the DataFrame will represent one CDA `subject` row (possibly with related data from other tables appended to it, according to user directives).

OR

returns nothing, but writes results to a user-specified TSV file

---

---
title: get_file_data()
---

Get CDA file rows ('result rows') that match user-specified criteria.


```
get_file_data(
    *search_terms,
    match_all=None,
    match_any=None,
    match_from_file={'input_file': '', 'input_column': '', 'cda_column_to_match': ''},
    data_source=None,
    add_columns=None,
    exclude_columns=None,
    collate_results=False,
    return_data_as='dataframe',
    output_file=''
)
```

## Arguments

### search_terms
( zero or more strings; optional: ):
One or more search terms (including phrases), all of which must be
associated with each result row. Users can add a wildcard character * to
either or both ends of each search term to enable partial matches
to longer values. Example:
    get_file_data( 'kidney', 'adeno*', 'latino' )

### match_all 
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
ALL of which must be met by all result rows.

### match_any 
( string or list of strings; optional ):
One or more conditions, expressed as filter strings (see below),
AT LEAST ONE of which must be met by all result rows.

### match_from_file 
( 3-element dictionary of strings; optional ):
A dictionary containing 3 named elements:
    1. 'input_file': The name of a (local) TSV file (with column names in its first row)
    2. 'input_column': The name of a column in that TSV
    3. 'cda_column_to_match': The name of a CDA column
Restrict result rows to those where the value of the given CDA
column matches at least one value from the given column
in the given TSV file.

### data_source 
( string or list of strings; optional ):
Restrict results to those deriving from the given upstream
data source(s). Current valid values are 'GDC', 'IDC', 'PDC',
'GC' and 'ICDC'. (Default: no filter.)

### add_columns 
( string or list of strings; optional ):
One or more columns from a second table to add to result data.

### exclude_columns 
( string or list of strings; optional ):
One or more columns to remove from result data.

### collate_results
( boolean; optional ):
If True: for each result file, include a DataFrame collating
results linked to that file from each non-file table that was
queried. Otherwise, for each result file, include a list of
unique values associated with that file from each non-file
column that was queried. Defaults to False.

### return_data_as
( string; optional: 'dataframe' or 'tsv' ):
Specify how to return results: as a pandas DataFrame,
or as output written to a TSV file named by the user. If this
argument is omitted, the default is to return results as a DataFrame.
    
### output_file
( string; optional ):
 If return_data_as='tsv' is specified, `output_file` should contain a
resolvable path to a file into which tab-delimited results will be
written.

## Filter strings
Filter strings are expressions of the form "COLUMN_NAME OP VALUE"
(note in particular that the whitespace surrounding OP is required),
where

- COLUMN_NAME is a searchable CDA column (see the columns() function
for details)

- OP is one of: `< <=  > >= = !=`

- VALUE is a particular value of whatever data type is stored
in COLUMN_NAME (see the columns() function for details), or
the special keyword NULL, indicating the filter should match
missing (null) values in COLUMN_NAME.

Operators `=` and `!=` will work on numeric, boolean and string VALUEs.

Operators `< <= > >=` will only work on numeric VALUEs.

Users can require partial matches to string VALUEs by adding `*` to either or
both ends. For example:

`diagnosis = *duct*`

`sex = F*`

String VALUEs need not be quoted inside of filter strings. For example, to include
the filters specified just above in the `match_all` argument, when querying
the `file` table, we can write:

`get_file_data( match_all=[ 'diagnosis = *duct*', 'sex = F*' ] )`

NULL is a special VALUE which can be used to match missing data. For
example, to get CDA file data for which the `cause_of_death` field
is missing data, we can write:

`get_file_data( match_all=[ 'cause_of_death = NULL' ] )`

## Returns
(Default) A pandas.DataFrame containing CDA file data matching the user-specified filter criteria. The DataFrame's named columns will match columns in the `file` table plus any optional user-added columns from other tables, and each row in the DataFrame will represent one CDA `file` row (possibly with related data from other tables appended to it, according to user directives).

OR

returns nothing, but writes results to a user-specified TSV file

---

---
title: intersect_subject_results()
---

Combine two or more DataFrames produced by get_subject_data() via intersection: merge result data for
all subjects present in all input DataFrames.

```
intersect_subject_results(*result_dfs_to_merge, ignore_added_columns=False)
```

## Arguments

### two or more DataFrames returned by get_subject_data()

### ignore_added_columns
( boolean; optional ):
Merge only columns from the subject table: avoids breakages in
cases where added extra (non-subject) columns can't be merged due
to differences in how similar but different upstream queries produced
the results we're trying to merge.
(Default: False: try to merge subject data plus all extra data appearing in
all input DataFrames.)

## Returns:
A pandas.DataFrame containing combined metadata about all subject rows that
appear in all input DataFrames, including by default all associated 
non-subject data present in all input DataFrames.

---

---
title: intersect_file_results()
---

Combine two or more DataFrames produced by get_file_data() via intersection: merge result data for
all files present in all input DataFrames.

```
intersect_file_results(*result_dfs_to_merge, ignore_added_columns=False)
```

## Arguments

### two or more DataFrames returned by get_file_data()

### ignore_added_columns
( boolean; optional ):
Merge only columns from the file table: avoids breakages in
cases where added extra (non-file) columns can't be merged due
to differences in how similar but different upstream queries produced
the results we're trying to merge.
(Default: False: try to merge file data plus all extra data appearing in
all input DataFrames.)

## Returns:
A pandas.DataFrame containing combined metadata about all file rows that
appear in all input DataFrames, including by default all associated 
non-file data present in all input DataFrames.

---

---
title: cda_functions()
---

Returns a list of cdapython functions useful for both scripting and interactive data sessions.

`cda_functions()`
