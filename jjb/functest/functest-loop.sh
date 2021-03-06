#!/bin/bash
set +e

branch=${GIT_BRANCH##*/}
[[ "$PUSH_RESULTS_TO_DB" == "true" ]] && flags+="-r"
if [[ "$BRANCH" =~ 'brahmaputra' ]]; then
    cmd="${FUNCTEST_REPO_DIR}/docker/run_tests.sh -s ${flags}"
elif [[ "$BRANCH" =~ 'colorado' ]]; then
    cmd="python ${FUNCTEST_REPO_DIR}/ci/run_tests.py -t all ${flags}"
else
    cmd="python ${FUNCTEST_REPO_DIR}/functest/ci/run_tests.py -t all ${flags}"
fi
container_id=$(docker ps -a | grep opnfv/functest | awk '{print $1}' | head -1)
docker exec $container_id $cmd

ret_value=$?
ret_val_file="${HOME}/opnfv/functest/results/${BRANCH##*/}/return_value"
echo ${ret_value}>${ret_val_file}

exit 0
