#!/usr/bin/python
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
import datetime
import jinja2
import os
import requests
import sys
import time
import yaml

import reportingUtils as utils
import reportingConf as conf
import testCase as tc
import scenarioResult as sr

testCases4Validation = []
otherTestCases = []

# init just tempest to get the list of scenarios
# as all the scenarios run Tempest
tempest = tc.TestCase("tempest_smoke_serial", "functest", -1)

# Retrieve the Functest configuration to detect which tests are relevant
# according to the installer, scenario
# cf = "https://git.opnfv.org/cgit/functest/plain/ci/config_functest.yaml"
cf = "https://git.opnfv.org/cgit/functest/plain/ci/testcases.yaml"
response = requests.get(cf)
functest_yaml_config = yaml.load(response.text)

print "****************************************"
print "*   Generating reporting.....          *"
print ("*   Data retention = %s days           *" % conf.PERIOD)
print "*                                      *"
print "****************************************"

# Retrieve test cases of Tier 1 (smoke)
config_tiers = functest_yaml_config.get("tiers")

# we consider Tier 1 (smoke),2 (sdn suites) and 3 (features)
# to validate scenarios
# Tier > 4 are not used to validate scenarios but we display the results anyway
# tricky thing for the API as some tests are Functest tests
# other tests are declared directly in the feature projects
for tier in config_tiers:
    if tier['order'] > 0 and tier['order'] < 3:
        for case in tier['testcases']:
            testCases4Validation.append(tc.TestCase(case['name'],
                                                    "functest",
                                                    case['dependencies']))
    elif tier['order'] == 3:
        for case in tier['testcases']:
            testCases4Validation.append(tc.TestCase(case['name'],
                                                    case['name'],
                                                    case['dependencies']))
    elif tier['order'] > 3:
        for case in tier['testcases']:
            otherTestCases.append(tc.TestCase(case['name'],
                                              "functest",
                                              case['dependencies']))

# For all the versions
for version in conf.versions:
    # For all the installers
    for installer in conf.installers:
        # get scenarios
        scenario_results = utils.getScenarios(tempest, installer, version)
        scenario_stats = utils.getScenarioStats(scenario_results)
        items = {}
        scenario_result_criteria = {}

        # For all the scenarios get results
        for s, s_result in scenario_results.items():
            # Green or Red light for a given scenario
            nb_test_runnable_for_this_scenario = 0
            scenario_score = 0

            testCases2BeDisplayed = []
            # Check if test case is runnable / installer, scenario
            # for the test case used for Scenario validation
            try:
                print ("---------------------------------")
                print ("installer %s, version %s, scenario %s:" %
                       (installer, version, s))

                # 1) Manage the test cases for the scenario validation
                # concretely Tiers 0-3
                for test_case in testCases4Validation:
                    test_case.checkRunnable(installer, s,
                                            test_case.getConstraints())
                    print ("testcase %s is %s" % (test_case.getName(),
                                                  test_case.isRunnable))
                    time.sleep(1)
                    if test_case.isRunnable:
                        dbName = test_case.getDbName()
                        name = test_case.getName()
                        project = test_case.getProject()
                        nb_test_runnable_for_this_scenario += 1
                        print (" Searching results for case %s " %
                               (dbName))
                        result = utils.getResult(dbName, installer, s, version)
                        print " >>>> Test result=" + str(result)
                        test_case.setCriteria(result)
                        test_case.setIsRunnable(True)
                        testCases2BeDisplayed.append(tc.TestCase(name,
                                                                 project,
                                                                 "",
                                                                 result,
                                                                 True,
                                                                 1))
                        scenario_score = scenario_score + result

                # 2) Manage the test cases for the scenario qualification
                # concretely Tiers > 3
                for test_case in otherTestCases:
                    test_case.checkRunnable(installer, s,
                                            test_case.getConstraints())
                    print ("testcase %s is %s" % (test_case.getName(),
                                                  test_case.isRunnable))
                    time.sleep(1)
                    if test_case.isRunnable:
                        dbName = test_case.getDbName()
                        name = test_case.getName()
                        project = test_case.getProject()
                        print (" Searching results for case %s " %
                               (dbName))
                        result = utils.getResult(dbName, installer, s, version)
                        test_case.setCriteria(result)
                        test_case.setIsRunnable(True)
                        testCases2BeDisplayed.append(tc.TestCase(name,
                                                                 project,
                                                                 "",
                                                                 result,
                                                                 True,
                                                                 4))

                    items[s] = testCases2BeDisplayed
            except:
                print ("Error: installer %s, version %s, scenario %s" %
                       (installer, version, s))
                print "No data available , error %s " % (sys.exc_info()[0])

            # **********************************************
            # Evaluate the results for scenario validation
            # **********************************************
            # the validation criteria = nb runnable tests x 3
            # because each test case = 0,1,2 or 3
            scenario_criteria = nb_test_runnable_for_this_scenario * 3
            # if 0 runnable tests set criteria at a high value
            if scenario_criteria < 1:
                scenario_criteria = conf.MAX_SCENARIO_CRITERIA

            s_score = str(scenario_score) + "/" + str(scenario_criteria)
            s_status = "KO"
            if scenario_score < scenario_criteria:
                print (">>>> scenario not OK, score = %s/%s" %
                       (scenario_score, scenario_criteria))
                s_status = "KO"
            else:
                print ">>>>> scenario OK, save the information"
                s_status = "OK"
                path_validation_file = ("./release/" + version +
                                        "/validated_scenario_history.txt")
                with open(path_validation_file, "a") as f:
                    time_format = "%Y-%m-%d %H:%M"
                    info = (datetime.datetime.now().strftime(time_format) +
                            ";" + installer + ";" + s + "\n")
                    f.write(info)

            scenario_result_criteria[s] = sr.ScenarioResult(s_status, s_score)
            print "--------------------------"

        templateLoader = jinja2.FileSystemLoader(os.path.dirname
                                                 (os.path.abspath
                                                  (__file__)))
        templateEnv = jinja2.Environment(loader=templateLoader)

        TEMPLATE_FILE = "./template/index-status-tmpl.html"
        template = templateEnv.get_template(TEMPLATE_FILE)

        outputText = template.render(scenario_stats=scenario_stats,
                                     scenario_results=scenario_result_criteria,
                                     items=items,
                                     installer=installer,
                                     period=conf.PERIOD,
                                     version=version)

        with open("./release/" + version +
                  "/index-status-" + installer + ".html", "wb") as fh:
            fh.write(outputText)
