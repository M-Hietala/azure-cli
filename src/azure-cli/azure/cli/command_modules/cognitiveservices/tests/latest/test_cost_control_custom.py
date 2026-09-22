# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import unittest
from unittest import mock

from azure.core.serialization import NULL
from azure.cli.core.azclierror import InvalidArgumentValueError, MutuallyExclusiveArgumentError

from azure.cli.command_modules.cognitiveservices._params import (
    _parse_cost_control_connections,
    _parse_cost_control_id,
)
from azure.cli.command_modules.cognitiveservices.custom import update
from azure.cli.command_modules.cognitiveservices.custom import (
    deployment_begin_create_or_update,
    deployment_update,
)
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentModel, DeploymentProperties, Sku


ACCOUNT_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/"
    "resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-account"
)
COST_CONTROL_ID = ACCOUNT_ID + "/costControls/test-control"
CONNECTION_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/"
    "resourceGroups/test-rg/providers/Microsoft.MachineLearningServices/"
    "workspaces/test-workspace/connections/test-connection"
)


class CognitiveServicesCostControlAccountUnitTests(unittest.TestCase):

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_accounts_cost_control"
    )
    def test_update_sets_typed_cost_control_properties(self, preview_client_factory):
        client = mock.Mock()
        preview_client = preview_client_factory.return_value

        update(
            cmd=mock.Mock(),
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            sku_name="S0",
            cost_control_ids=[COST_CONTROL_ID],
            cost_control_connections={
                "appInsightsConnectionId": CONNECTION_ID,
                "eventGridConnectionId": None,
            },
        )

        client.begin_update.assert_not_called()
        parameters = preview_client.begin_update.call_args.args[2]
        self.assertEqual(parameters.properties.cost_control_ids, [COST_CONTROL_ID])
        self.assertEqual(
            parameters.properties.cost_control_connections.app_insights_connection_id,
            CONNECTION_ID,
        )
        connections = dict(parameters.properties.cost_control_connections)
        self.assertIn("eventGridConnectionId", connections)
        self.assertIs(connections["eventGridConnectionId"], NULL)

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_accounts_cost_control"
    )
    def test_update_clears_cost_control_connections(self, preview_client_factory):
        client = mock.Mock()

        update(
            cmd=mock.Mock(),
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            sku_name="S0",
            clear_cost_control_connections=True,
        )

        parameters = preview_client_factory.return_value.begin_update.call_args.args[2]
        properties = dict(parameters.properties)
        self.assertIn("costControlConnections", properties)
        self.assertIsNone(properties["costControlConnections"])

    def test_update_rejects_multiple_cost_controls(self):
        with self.assertRaises(InvalidArgumentValueError):
            update(
                cmd=mock.Mock(),
                client=mock.Mock(),
                resource_group_name="test-rg",
                account_name="test-account",
                sku_name="S0",
                cost_control_ids=[COST_CONTROL_ID, COST_CONTROL_ID],
            )

    def test_update_rejects_connections_and_clear(self):
        with self.assertRaises(MutuallyExclusiveArgumentError):
            update(
                cmd=mock.Mock(),
                client=mock.Mock(),
                resource_group_name="test-rg",
                account_name="test-account",
                sku_name="S0",
                cost_control_connections={"appInsightsConnectionId": CONNECTION_ID},
                clear_cost_control_connections=True,
            )

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_accounts_cost_control"
    )
    def test_update_without_cost_control_uses_existing_client(self, preview_client_factory):
        client = mock.Mock()

        update(
            cmd=mock.Mock(),
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            sku_name="S0",
            tags={"environment": "test"},
        )

        preview_client_factory.assert_not_called()
        client.begin_update.assert_called_once()

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_accounts_cost_control"
    )
    def test_update_combines_existing_and_cost_control_properties(self, preview_client_factory):
        preview_client = preview_client_factory.return_value

        update(
            cmd=mock.Mock(),
            client=mock.Mock(),
            resource_group_name="test-rg",
            account_name="test-account",
            sku_name="S0",
            tags={"environment": "test"},
            allow_project_management=True,
            cost_control_ids=[COST_CONTROL_ID],
        )

        parameters = preview_client.begin_update.call_args.args[2]
        self.assertEqual(parameters.tags, {"environment": "test"})
        self.assertTrue(parameters.properties.allow_project_management)
        self.assertEqual(parameters.properties.cost_control_ids, [COST_CONTROL_ID])

    def test_cost_control_parsers(self):
        self.assertEqual(_parse_cost_control_id(COST_CONTROL_ID), COST_CONTROL_ID)
        self.assertEqual(
            _parse_cost_control_connections(
                '{"appInsightsConnectionId":"' + CONNECTION_ID + '","eventGridConnectionId":null}'
            ),
            {
                "appInsightsConnectionId": CONNECTION_ID,
                "eventGridConnectionId": None,
            },
        )

    def test_cost_control_id_parser_rejects_account_id(self):
        with self.assertRaises(InvalidArgumentValueError):
            _parse_cost_control_id(ACCOUNT_ID)

    def test_connection_parser_rejects_non_object(self):
        with self.assertRaises(InvalidArgumentValueError):
            _parse_cost_control_connections("[]")

    def test_connection_parser_rejects_unknown_property(self):
        with self.assertRaises(InvalidArgumentValueError):
            _parse_cost_control_connections('{"unsupported":"value"}')

    def test_connection_parser_rejects_invalid_resource_id(self):
        with self.assertRaises(InvalidArgumentValueError):
            _parse_cost_control_connections('{"appInsightsConnectionId":"invalid"}')


class CognitiveServicesCostControlDeploymentUnitTests(unittest.TestCase):

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_deployments_cost_control"
    )
    def test_create_with_cost_control_uses_preview_client(self, preview_client_factory):
        client = mock.Mock()
        preview_client = preview_client_factory.return_value

        deployment_begin_create_or_update(
            cmd=mock.Mock(),
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            deployment_name="test-deployment",
            model_format="OpenAI",
            model_name="gpt-4.1",
            model_version="2025-04-14",
            sku_name="GlobalStandard",
            sku_capacity=10,
            cost_control_ids=[COST_CONTROL_ID],
        )

        client.begin_create_or_update.assert_not_called()
        parameters = preview_client.begin_create_or_update.call_args.args[3]
        self.assertEqual(parameters.properties.cost_control_ids, [COST_CONTROL_ID])
        self.assertEqual(parameters.properties.model.name, "gpt-4.1")
        self.assertEqual(parameters.sku.name, "GlobalStandard")

    @mock.patch(
        "azure.cli.command_modules.cognitiveservices.custom.cf_deployments_cost_control"
    )
    def test_create_without_cost_control_uses_existing_client(self, preview_client_factory):
        client = mock.Mock()

        deployment_begin_create_or_update(
            cmd=mock.Mock(),
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            deployment_name="test-deployment",
            model_format="OpenAI",
            model_name="gpt-4.1",
            model_version="2025-04-14",
        )

        preview_client_factory.assert_not_called()
        client.begin_create_or_update.assert_called_once()

    def test_update_preserves_deployment_and_sets_cost_control(self):
        client = mock.Mock()
        deployment = Deployment(
            properties=DeploymentProperties(
                model=DeploymentModel(format="OpenAI", name="gpt-4.1", version="2025-04-14")
            ),
            sku=Sku(name="GlobalStandard", capacity=10),
            tags={"environment": "test"},
        )
        client.get.return_value = deployment

        deployment_update(
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            deployment_name="test-deployment",
            cost_control_ids=[COST_CONTROL_ID],
        )

        updated = client.begin_create_or_update.call_args.args[3]
        self.assertIs(updated, deployment)
        self.assertEqual(updated.properties.cost_control_ids, [COST_CONTROL_ID])
        self.assertEqual(updated.properties.model.name, "gpt-4.1")
        self.assertEqual(updated.sku.capacity, 10)
        self.assertEqual(updated.tags, {"environment": "test"})

    def test_update_supports_detach(self):
        client = mock.Mock()
        client.get.return_value = Deployment(properties=DeploymentProperties())

        deployment_update(
            client=client,
            resource_group_name="test-rg",
            account_name="test-account",
            deployment_name="test-deployment",
            cost_control_ids=[],
        )

        updated = client.begin_create_or_update.call_args.args[3]
        self.assertEqual(updated.properties.cost_control_ids, [])

    def test_update_rejects_multiple_cost_controls(self):
        with self.assertRaises(InvalidArgumentValueError):
            deployment_update(
                client=mock.Mock(),
                resource_group_name="test-rg",
                account_name="test-account",
                deployment_name="test-deployment",
                cost_control_ids=[COST_CONTROL_ID, COST_CONTROL_ID],
            )

    def test_create_rejects_multiple_cost_controls(self):
        with self.assertRaises(InvalidArgumentValueError):
            deployment_begin_create_or_update(
                cmd=mock.Mock(),
                client=mock.Mock(),
                resource_group_name="test-rg",
                account_name="test-account",
                deployment_name="test-deployment",
                model_format="OpenAI",
                model_name="gpt-4.1",
                model_version="2025-04-14",
                cost_control_ids=[COST_CONTROL_ID, COST_CONTROL_ID],
            )


if __name__ == "__main__":
    unittest.main()