#!/bin/bash
set -u ;  # exit  if you try to use an uninitialized variable
#set -x ;  # print out the statements as they are being executed
set -e ;  #  bash exits if any statement returns a non-true return value
#set -o errexit ;  # exit if any statement returns a non-true return value

#.... setup
basePath0=/dataVault/dataQubiC_APS2024/

readFidA=' 0.99 0.99 ' ; readFidB=' 0.97 0.93 ' 
czFidA=0.99 ; czFidB=0.95

basePath=${basePath0}/readA_czA ; readFid=$readFidA ; czFid=$czFidA
#basePath=${basePath0}/readB_czB ; readFid=$readFidB ; czFid=$czFidB
basePath=${basePath0}/readA_czB ; readFid=$readFidA ; czFid=$czFidB
basePath=${basePath0}/readB_czA ; readFid=$readFidB ; czFid=$czFidA


mkdir $basePath ; cd  $basePath; mkdir    log  meas post ;   cd -

comArgs="  --numShots  100000 --noiseConf  qubicAps24  --noise_czFidel  $czFid  --noise_readFidel $readFid -p --cycles  1 11 21 "

start_time=$SECONDS  # Capture start time
k=0 # Initialize a counter for the generated names
for T1 in $(seq 50 10 150); do  # START INCREMENT END
    for T2 in $(seq 10 10 100); do
        # Skip the loop iteration if T2 > 2*T1
        if [ $T2 -gt $((2*T1)) ]; then	
            continue
        fi
        expN="bell_${T1}_${T2}"
	k=$[ $k + 1 ] # Increment the counter
	elaT=$(($SECONDS - start_time))  # Calculate elapsed time
        echo $k elaT=$elaT $expN  $comArgs
	./run_aer_job.py --basePath  $basePath  --expName $expN  --noise_T1T2 $T1 $T2  $comArgs  >& ${basePath}/log/$expN.txt

    done
done

echo "Total generated names: $k"
date

#Total generated names: 110
#real	11m50.455s
