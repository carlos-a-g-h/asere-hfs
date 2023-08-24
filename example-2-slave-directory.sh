#!/bin/bash

# The slave directory can contain paths that can be outside of the scope of the
# master directory when they are resolved. This can happen with mount points and
# symbolic links mostly

# For the purpose of this small test, some files will be created first before
# running the server

mkdir -p example-2-test/master-dir
mkdir -p example-2-test/slave-directory
echo "file contents" > "example-2-test/master-dir/some file inside the master directory.txt"
ln -sr "example-2-test/slave-directory/" "example-2-test/master-dir/link to slave"
echo "more stuff" > "example-2-test/slave-directory/file inside the slave dir.txt"

find example-2-test

./asere-hfs.amd64 --port 8080 --master example-2-test/master-dir --slave example-2-test/slave-directory
