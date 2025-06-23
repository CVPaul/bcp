PWD=`pwd`
for cmd in 'show' 'debug' 'income' 'download'; do
    ln -sf ${PWD}/$cmd $CONDA_PREFIX/bin/
done
