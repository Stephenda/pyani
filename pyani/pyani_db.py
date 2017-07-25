# -*- coding: utf-8 -*-
"""pyani_db.py

This module provides useful functions for creating and manipulating pyani's
SQLite3 databases

(c) The James Hutton Institute 2016-2017
Author: Leighton Pritchard

Contact:
leighton.pritchard@hutton.ac.uk

Leighton Pritchard,
Information and Computing Sciences,
James Hutton Institute,
Errol Road,
Invergowrie,
Dundee,
DD6 9LH,
Scotland,
UK

The MIT License

Copyright (c) 2016-2017 The James Hutton Institute

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sqlite3

# SQL SCRIPTS
#==============
# The following is SQL for various database admin tasks, defined here to
# be out of the way when reading code.

# Create database tables
#
# genomes            - a row of data, one per genome
# runs               - a row of data, one per pyani run
# comparisons        - a row of data, one per pairwise comparison
# run_genomes        - table providing many:many comparisons
#
# The intention is that a run applies to some/all genomes from the genomes
# table, and that all the relevant pairwise comparisons/results are stored
# in the comparisons table.
#
# Information about the run (when it was run, what command/method, etc.) are
# stored in the runs table.
#
# All genomes (whether used or not) are described in the genomes table. An MD5
# hash is used to uniquely identify/validate a genome that is used for any
# comparison. The path to the source data, and a description of the genome are
# stored. We expect the path information to be live, so that a comparison may
# be run or re-run. The hash will be used to verify the contents of the file
# at the end of the path, when there is a run.
#
# Each pairwise comparison is stored (forward/reverse comparisons are stored
# separately, to allow method flexibility) in the comparisons table. The
# comparisons are tied directly to genomes, but only transitively to a
# particular run; this reduces redundancy, and allows pairwise comparison
# data to be used without recalculation, if the same input genome,
# path/hash, and analysis settings (fragsize for ANIb/ANIblastall and maxmatch
# for NUCmer),  are provided.
#
# The runs_genomes table provides a link so that each genome is associated with
# all runs in which it has participated, and each run can be associated with
# all the genomes that it has participated in.

# Create database tables
SQL_CREATEDB = """
   DROP TABLE IF EXISTS genomes;
   CREATE TABLE genomes (genome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                         hash TEXT,
                         path TEXT,
                         description TEXT
                        );
   DROP TABLE IF EXISTS runs;
   CREATE TABLE runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      method TEXT,
                      cmdline TEXT,
                      date TEXT,
                      status TEXT
                     );
   DROP TABLE IF EXISTS runs_genomes;
   CREATE TABLE runs_genomes(run_id INTEGER NOT NULL,
                             genome_id INTEGER NOT NULL,
                             PRIMARY KEY (run_id, genome_id),
                             FOREIGN KEY(run_id) REFERENCES
                                                   runs(run_id),
                             FOREIGN KEY(genome_id) REFERENCES 
                                                      genomes(genome_id)
                            );
   DROP TABLE IF EXISTS comparisons;
   CREATE TABLE comparisons (query_id INTEGER NOT NULL,
                             subject_id INTEGER NOT NULL,
                             identity REAL,
                             coverage REAL,
                             mismatches REAL,
                             aligned_length REAL,
                             program TEXT,
                             version TEXT,
                             fragsize TEXT,
                             maxmatch TEXT,
                             PRIMARY KEY (query_id, subject_id)
                            );
   """

# Create indexes on hash in genome table
# The hash index is a standard single column index
# The hashpath index is a UNIQUE index to ensure that we don't duplicate the
# exact same file (though copies of the file in other places are allowed).
SQL_INDEXGENOMEHASH = """
   DROP INDEX IF EXISTS genomehash_index;
   CREATE INDEX genomehash_index ON genomes (hash);
   DROP INDEX IF EXISTS genomehashpath_index;
   CREATE UNIQUE INDEX genomehashpath_index ON genomes (hash, path);
"""

# Add a genome to the database
SQL_ADDRUN = """
   INSERT INTO runs (method, cmdline, date, status) VALUES (?, ?, ?, ?);
"""

# Add a genome to the database
SQL_ADDGENOME = """
   INSERT INTO genomes (hash, path, description) VALUES (?, ?, ?);
"""

# Associate a run with a genome
SQL_ADDRUNGENOME = """
   INSERT INTO runs_genomes (run_id, genome_id) VALUES (?, ?);
"""

# Get a specific genome hash
SQL_GETGENOMEHASH = """
   SELECT * FROM genomes WHERE hash=?;
"""

# Get a specific genome path
SQL_GETGENOMEPATH = """
   SELECT path FROM genomes WHERE genome_id=?;
"""

# Get a specific genome hash/path combination
SQL_GETGENOMEHASHPATH = """
   SELECT * FROM genomes WHERE hash=? AND path=?;
"""

# Get all genome IDs associated with a specified run
SQL_GETGENOMESBYRUN = """
   SELECT genome_id FROM runs_genomes WHERE run_id=?;
"""

# Get a comparison (if it exists)
SQL_GETCOMPARISON = """
   SELECT * FROM comparisons WHERE query_id=? AND subject_id=? AND
                                   program=? AND version=? AND
                                   fragsize=? AND maxmatch=?;
"""


# Create an empty pyani SQLite3 database
def create_db(path):
    """Create an empty pyani SQLite3 database at the passed path."""
    conn = sqlite3.connect(path)
    with conn:
        cur = conn.cursor()
        cur.executescript(SQL_CREATEDB)
        cur.executescript(SQL_INDEXGENOMEHASH)


# Add a new run to the database
def add_run(dbpath, method, cmdline, date, status):
    """Add run information to the passed database, and return a run ID."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        cur.execute(SQL_ADDRUN, (method, cmdline, date, status))
    return cur.lastrowid

        
# Add a new genome to the database
def add_genome(dbpath, hash, filepath, desc):
    """Add a genome to the passed SQLite3 database."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        # The following line will fail if the genome is already in the
        # database, i.e. if the hash is not unique
        cur.execute(SQL_ADDGENOME, (hash, filepath, desc))
    return cur.lastrowid


# Associate a run ID with a genome ID
def add_genome_to_run(dbpath, run_id, genome_id):
    """Associate a run with a genome."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        cur.execute(SQL_ADDRUNGENOME, (run_id, genome_id))
    return cur.lastrowid


# Return the row corresponding to a single genome, defined by hash
def get_genome(dbpath, hash, path=None):
    """Returns genome data if the passed hash is in the genomes table."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        if path is None:
            cur.execute(SQL_GETGENOMEHASH, (hash,))
        else:
            cur.execute(SQL_GETGENOMEHASHPATH, (hash, path))
        result = cur.fetchall()
    return result


# Return the filepath associated with a genome_id
def get_genome_path(dbpath, genome_id):
    """Returns the file path associated with a genome_id."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        cur.execute(SQL_GETGENOMEPATH, (genome_id, ))
        result = cur.fetchone()
    return result[0]


# Return genome IDs associated with a specific run
def get_genome_ids_by_run(dbpath, run_id):
    """Returns list of genome IDs corresponding to the run with passed ID."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        cur.execute(SQL_GETGENOMESBYRUN, (run_id,))
        result = cur.fetchall()
    return [gid[0] for gid in result]


# Check if a comparison has been performed
def get_comparison(dbpath, subj_id, targ_id, program, version,
                   fragsize=None, maxmatch=None):
    """Returns the genome ID of a specified comparison."""
    conn = sqlite3.connect(dbpath)
    with conn:
        cur = conn.cursor()
        cur.execute(SQL_GETCOMPARISON, (subj_id, targ_id, program, version,
                                        fragsize, maxmatch))
        result = cur.fetchone()
    return result