#!/usr/bin/env sh
## Template for use with a file containing a list of commands to run
## Example call:
##     EXPT_FILE=scripts/experiments.txt
##     NR_EXPTS=`cat ${EXPT_FILE} | wc -l`
##     MAX_PARALLEL_JOBS=4 
##     sbatch --array=1-${NR_EXPTS}%${MAX_PARALLEL_JOBS} slurm_template.sh $EXPT_FILE

#SBATCH -N 1	  # nodes requested
#SBATCH -n 1	  # tasks requested
#SBATCH --mem=4000  # memory in Mb
#SBATCH -t 00:30:00  # time requested in hour:minute:seconds
#SBATCH --cpus-per-task=1  # number of cpus to use - there are 32 on each node.


set -e  # make script bail out after first error


# slurm info for logging
echo "I'm running on ${SLURM_JOB_NODELIST}"
dt=$(date '+%d/%m/%Y %H:%M:%S');
echo $dt


# Set environment variables for input and output data
echo 'Setting experiment environment variables'
export STUDENT_ID=$(whoami)
export SCRATCH_HOME=/disk/scratch/${STUDENT_ID}
mkdir -p ${SCRATCH_HOME}
export TMPDIR=${SCRATCH_HOME}
export TMP=${SCRATCH_HOME}
export CLUSTER_HOME=$HOME

code_repo_home=${CLUSTER_HOME}/git/midi_degradation_toolkit
output_dir=${code_repo_home}/output
distfs_data_home="${code_repo_home}/acme"
scratch_data_home="${SCRATCH_HOME}/data/acme"
mkdir -p ${scratch_data_home}


# Move data from distrbuted filesystem to scratch dir on cluster node
for corpus in cmd pr; do
    for split in train valid test; do
        fn="${split}_${corpus}_corpus.csv"
        source="${distfs_data_home}/${fn}"
        target="${scratch_data_home}/${fn}"
        rsync -ua --progress ${source} ${target}
    done
done

for fn in degradation_ids.csv metadata.csv; do
    source="${distfs_data_home}/${fn}"
    target="${scratch_data_home}/${fn}"
    rsync -ua --progress ${source} ${target}
done


echo "============"
echo "job finished successfully"