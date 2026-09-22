# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os

from azure.cli.testsdk import ResourceGroupPreparer, ScenarioTest
from azure.cli.testsdk.scenario_tests.decorators import live_only


TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@live_only()
class CognitiveServicesCostControlScenarioTests(ScenarioTest):

    @ResourceGroupPreparer(
        name_prefix="az-cli-cost-control-test-rg-",
        location="westus2",
        random_name_length=38,
    )
    def test_cognitiveservices_cost_control(self, resource_group):
        self.kwargs.update({
            "account_name": self.create_random_name("test-account-", 23),
            "cost_control_name": "test-control",
            "display_name": "Test Cost Control",
            "updated_display_name": "Updated Test Cost Control",
            "location": "westus2",
            "resource_group": resource_group,
            "rules_file": os.path.join(TEST_DIR, "data", "cost_control_rules.json"),
        })

        account = self.cmd(
            "cognitiveservices account create "
            "--resource-group {resource_group} "
            "--name {account_name} "
            "--kind AIServices "
            "--sku S0 "
            "--location {location} "
            "--yes"
        ).get_output_in_json()
        self.kwargs["account_id"] = account["id"]

        cost_control = self.cmd(
            "cognitiveservices account costcontrol create "
            "--resource-group {resource_group} "
            "--account-name {account_name} "
            "--cost-control-name {cost_control_name} "
            "--display-name '{display_name}' "
            "--rules '@{rules_file}'",
            checks=[
                self.check("name", "{cost_control_name}"),
                self.check("properties.displayName", "{display_name}"),
                self.check("properties.rules[0].name", "monthly-account-budget"),
            ],
        ).get_output_in_json()
        self.kwargs["cost_control_id"] = cost_control["id"]

        self.cmd(
            "cognitiveservices account update "
            "--resource-group {resource_group} "
            "--name {account_name} "
            "--cost-control-ids {cost_control_id}",
            checks=[self.check("properties.costControlIds[0]", "{cost_control_id}")],
        )

        self.cmd(
            "cognitiveservices account costcontrol list "
            "--resource-group {resource_group} "
            "--account-name {account_name}",
            checks=[self.check("length(@)", 1)],
        )

        self.cmd(
            "cognitiveservices account costcontrol show "
            "--resource-group {resource_group} "
            "--account-name {account_name} "
            "--cost-control-name {cost_control_name}",
            checks=[self.check("properties.displayName", "{display_name}")],
        )

        self.cmd(
            "cognitiveservices account costcontrol update "
            "--resource-group {resource_group} "
            "--account-name {account_name} "
            "--cost-control-name {cost_control_name} "
            "--display-name '{updated_display_name}'",
            checks=[
                self.check("properties.displayName", "{updated_display_name}"),
                self.check("properties.rules[0].name", "monthly-account-budget"),
            ],
        )

        self.cmd(
            "cognitiveservices account update "
            "--resource-group {resource_group} "
            "--name {account_name} "
            "--cost-control-ids",
            checks=[self.check("properties.costControlIds", [])],
        )

        self.cmd(
            "cognitiveservices account costcontrol delete "
            "--resource-group {resource_group} "
            "--account-name {account_name} "
            "--cost-control-name {cost_control_name} "
            "--yes"
        )

        self.cmd(
            "cognitiveservices account costcontrol list "
            "--resource-group {resource_group} "
            "--account-name {account_name}",
            checks=[self.check("length(@)", 0)],
        )