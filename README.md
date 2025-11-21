# python-apt wheel rocks

These rocks build python-apt wheels for all current Ubuntu platforms.

Basic usage:

Far each platform you want to build for, go into the directory and run:

```
git init
rockcraft remote-build
```

Once all remote builds are complete, extract the wheels from the rocks with:

```
./extract_rocks.sh */*.rock
```
