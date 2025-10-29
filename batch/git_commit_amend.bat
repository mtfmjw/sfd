echo off
call "%~dp0parameters.bat"

pushd %base_dir%

git add --all
git commit --amend --no-edit
git push --force-with-lease

popd