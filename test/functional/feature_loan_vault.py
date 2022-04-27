#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""Test vault."""

from decimal import Decimal
from test_framework.test_framework import DefiTestFramework

from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal, assert_raises_rpc_error
import calendar
import time

class VaultTest (DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [
                ['-txnotokens=0', '-amkheight=1', '-bayfrontheight=1', '-bayfrontgardensheight=1', '-eunosheight=1', '-txindex=1', '-fortcanningheight=1', '-fortcanninghillheight=300', '-jellyfish_regtest=1', '-simulatemainnet'],
                ['-txnotokens=0', '-amkheight=1', '-bayfrontheight=1', '-bayfrontgardensheight=1', '-eunosheight=1', '-txindex=1', '-fortcanningheight=1', '-fortcanninghillheight=300', '-jellyfish_regtest=1', '-simulatemainnet']
            ]
        self.vaults = []
        self.owner_addresses = []
        self.oracles = []

    def setup_loanschemes(self):
        self.nodes[0].createloanscheme(175, 3, 'LOAN0001')
        self.nodes[0].createloanscheme(150, 2.5, 'LOAN000A')
        self.nodes[0].createloanscheme(200, 2, 'LOAN0002')
        self.nodes[0].createloanscheme(350, 1.5, 'LOAN0003')
        self.nodes[0].createloanscheme(550, 1.5, 'LOAN0004')
        self.nodes[0].generate(1)
        self.nodes[0].setdefaultloanscheme('LOAN0001')
        self.nodes[0].generate(1)

    def create_vaults(self):
        owner_addr_0 = self.nodes[0].getnewaddress('', 'legacy')
        self.owner_addresses.append(owner_addr_0)
        vault_id_0 = self.nodes[0].createvault(owner_addr_0) # default loan scheme
        self.vaults.append(vault_id_0)

        owner_addr_1 = self.nodes[0].getnewaddress('', 'legacy')
        self.owner_addresses.append(owner_addr_1)
        vault_id_1 = self.nodes[0].createvault(owner_addr_1, 'LOAN0001')
        self.vaults.append(vault_id_1)
        vault_id_2 = self.nodes[0].createvault(owner_addr_1, 'LOAN0003')
        self.vaults.append(vault_id_2)
        vault_id_3 = self.nodes[0].createvault(owner_addr_1, 'LOAN0003')
        self.vaults.append(vault_id_3)
        self.nodes[0].generate(1)

    def setup_accounts_and_tokens(self):
        assert_equal(len(self.nodes[0].listtokens()), 1) # only one token == DFI
        self.nodes[0].generate(25)
        self.sync_blocks()
        self.nodes[1].generate(102)
        self.sync_blocks()

        self.nodes[1].createtoken({
            "symbol": "BTC",
            "name": "BTC token",
            "isDAT": True,
            "collateralAddress": self.nodes[1].get_genesis_keys().ownerAuthAddress
        })
        self.nodes[1].generate(1)
        self.sync_blocks()

        self.symbolDFI = "DFI"
        self.symbolBTC = "BTC"

        self.nodes[1].minttokens("10@" + self.symbolBTC)
        self.nodes[1].generate(1)
        self.sync_blocks()

        self.idDFI = list(self.nodes[0].gettoken(self.symbolDFI).keys())[0]
        self.idBTC = list(self.nodes[0].gettoken(self.symbolBTC).keys())[0]
        self.accountDFI = self.nodes[0].get_genesis_keys().ownerAuthAddress
        self.accountBTC = self.nodes[1].get_genesis_keys().ownerAuthAddress

        self.nodes[0].utxostoaccount({self.accountDFI: "100@" + self.symbolDFI})
        self.nodes[0].generate(1)
        self.nodes[0].setloantoken({
                            'symbol': "TSLA",
                            'name': "Tesla Token",
                            'fixedIntervalPriceId': "TSLA/USD",
                            'mintable': True,
                            'interest': 2})
        self.nodes[0].generate(1)

        self.nodes[0].setcollateraltoken({
                                    'token': self.idDFI,
                                    'factor': 1,
                                    'fixedIntervalPriceId': "DFI/USD"})

        self.nodes[0].setcollateraltoken({
                                    'token': self.idBTC,
                                    'factor': 0.8,
                                    'fixedIntervalPriceId': "BTC/USD"})

        self.nodes[0].generate(120)
        self.sync_blocks()
        self.nodes[0].setloantoken({
                                    'symbol': "DUSD",
                                    'name': "DUSD stable token",
                                    'fixedIntervalPriceId': "DUSD/USD",
                                    'mintable': True,
                                    'interest': 1})
        self.nodes[0].generate(120)



    def setup_oracles(self):
        oracle_address1 = self.nodes[0].getnewaddress("", "legacy")
        price_feeds1 = [{"currency": "USD", "token": "DFI"}, {"currency": "USD", "token": "BTC"}, {"currency": "USD", "token": "TSLA"}]
        oracle_id1 = self.nodes[0].appointoracle(oracle_address1, price_feeds1, 10)
        self.oracles.append(oracle_id1)
        self.nodes[0].generate(1)

        oracle1_prices = [{"currency": "USD", "tokenAmount": "1@DFI"}, {"currency": "USD", "tokenAmount": "1@BTC"}, {"currency": "USD", "tokenAmount": "1@TSLA"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(oracle_id1, timestamp, oracle1_prices)

        self.nodes[0].generate(120)

    def create_poolpairs(self):
        poolOwner = self.nodes[0].getnewaddress("", "legacy")
        self.nodes[0].createpoolpair({
            "tokenA": "DUSD",
            "tokenB": self.idDFI,
            "commission": Decimal('0.002'),
            "status": True,
            "ownerAddress": poolOwner,
            "pairSymbol": "DUSD-DFI",
        }, [])
        self.nodes[0].generate(1)

        self.nodes[0].minttokens("300@DUSD")
        self.nodes[0].generate(1)
        self.nodes[0].utxostoaccount({self.accountDFI: "100@" + self.symbolDFI})
        self.nodes[0].generate(1)
        self.nodes[0].addpoolliquidity({
            self.accountDFI: ["300@DUSD", "100@" + self.symbolDFI]
        }, self.accountDFI, [])
        self.nodes[0].generate(1)

        self.nodes[0].createpoolpair({
            "tokenA": "DUSD",
            "tokenB": "TSLA",
            "commission": Decimal('0.002'),
            "status": True,
            "ownerAddress": poolOwner,
            "pairSymbol": "DUSD-TSLA",
        }, [])
        self.nodes[0].generate(1)

        self.nodes[0].minttokens("100@TSLA")
        self.nodes[0].generate(1)
        self.nodes[0].minttokens("100@DUSD")
        self.nodes[0].generate(1)
        self.nodes[0].addpoolliquidity({
            self.accountDFI: ["100@TSLA", "100@DUSD"]
        }, self.accountDFI, [])
        self.nodes[0].generate(1)


    def setup(self):
        self.nodes[0].generate(120)
        self.setup_loanschemes()
        self.create_vaults()
        self.setup_oracles()
        self.setup_accounts_and_tokens()
        self.create_poolpairs()


    def createvault_with_invalid_parameters(self):
        try:
            self.nodes[0].createvault('ffffffffff')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('recipient script (ffffffffff) does not solvable/non-standard' in errorString)

        # Create vault with invalid loanschemeid and default owner address
        owner = self.nodes[0].getnewaddress('', 'legacy')
        try:
            self.nodes[0].createvault(owner, 'FAKELOAN')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Cannot find existing loan scheme with id FAKELOAN' in errorString)

    def listvaults_and_filtering(self):
        # check listvaults
        list_vault = self.nodes[0].listvaults()
        assert_equal(len(list_vault), 4)

        # Filetering
        # by owner_address
        list_vault = self.nodes[0].listvaults({ "ownerAddress": self.owner_addresses[1] })
        assert_equal(len(list_vault), 3)
        for vault in list_vault:
            assert_equal(vault["ownerAddress"], self.owner_addresses[1])

        # by loanSchemeId
        list_vault = self.nodes[0].listvaults({ "loanSchemeId": "LOAN0003" })
        assert_equal(len(list_vault), 2)
        for vault in list_vault:
            assert_equal(vault["loanSchemeId"], "LOAN0003")

        # Pagination
        # limit
        list_vault = self.nodes[0].listvaults({}, {"limit": 1})
        assert_equal(len(list_vault), 1)

        # including_include_start
        list_vault_include_start = self.nodes[0].listvaults({}, {"limit": 1, "including_start": False})
        assert_equal(len(list_vault_include_start), 1)
        assert(list_vault[0]['vaultId'] != list_vault_include_start[0]['vaultId'])
        startId = list_vault[0]['vaultId']

        # start
        list_vault_start = self.nodes[0].listvaults({}, {"start": startId})
        assert_equal(len(list_vault_start), 3)

        # start & include_start
        list_vault_start = self.nodes[0].listvaults({}, {"start": startId, "including_start": True})
        assert_equal(len(list_vault_start), 4)


    def test_feeburn(self):
        assert_equal(self.nodes[0].getburninfo()['feeburn'], Decimal('3'))

    def getvault_wrong_vault_address(self):
        try:
            self.nodes[0].getvault('5474b2e9bfa96446e5ef3c9594634e1aa22d3a0722cb79084d61253acbdf87bf')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Vault <5474b2e9bfa96446e5ef3c9594634e1aa22d3a0722cb79084d61253acbdf87bf> not found' in errorString)

    def test_getvault(self):
        vault = self.nodes[0].getvault(self.vaults[0])
        assert_equal(vault["loanSchemeId"], 'LOAN0001')
        assert_equal(vault["ownerAddress"], self.owner_addresses[0])
        assert_equal(vault["state"], "active")
        assert_equal(vault["collateralAmounts"], [])
        assert_equal(vault["loanAmounts"], [])
        assert_equal(vault["collateralValue"], Decimal(0))
        assert_equal(vault["loanValue"], Decimal(0))
        assert_equal(vault["informativeRatio"], Decimal('-1.00000000'))

    def updatevault_with_invalid_parameters(self):
        try:
            params = {}
            self.nodes[0].updatevault(self.vaults[0], params)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("At least ownerAddress OR loanSchemeId must be set" in errorString)

        # bad loan scheme id
        try:
            params = {'loanSchemeId': 'FAKELOAN'}
            self.nodes[0].updatevault(self.vaults[0], params)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Cannot find existing loan scheme with id FAKELOAN" in errorString)

        # bad owner address
        try:
            params = {'ownerAddress': 'ffffffffff'}
            self.nodes[0].updatevault(self.vaults[0], params)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Error: Invalid owner address" in errorString)

    def actions_on_vault_with_scheme_to_be_destroyed(self):
        # Create or update vault with loan scheme planned to be destroyed
        destruction_height = self.nodes[0].getblockcount() + 3
        self.nodes[0].destroyloanscheme('LOAN0002', destruction_height)
        self.nodes[0].generate(1)

        # create
        try:
            self.nodes[0].createvault(self.owner_addresses[0], 'LOAN0002') # default loan scheme
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Cannot set LOAN0002 as loan scheme, set to be destroyed on block 626" in error_str)

        # update
        try:
            params = {'loanSchemeId':'LOAN0002'}
            self.nodes[0].updatevault(self.vaults[1], params) # default loan scheme
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Cannot set LOAN0002 as loan scheme, set to be destroyed on block 626" in error_str)

    def update_vault_scheme(self):
        new_address = self.nodes[0].getnewaddress('', 'legacy')
        params = {'loanSchemeId': 'LOAN0001', 'ownerAddress': new_address}

        self.nodes[0].updatevault(self.vaults[1], params)
        self.nodes[0].generate(1)

        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['ownerAddress'], new_address)
        assert_equal(vault['loanSchemeId'], 'LOAN0001')
        # update global list after update
        self.owner_addresses[1] = new_address

    def automatic_update_after_loanscheme_delete(self):
        # update with non-default loan scheme and delete loan to check automatic update
        params = {'loanSchemeId': 'LOAN0003'}
        self.nodes[0].updatevault(self.vaults[1], params)
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['loanSchemeId'], 'LOAN0003')

        self.nodes[0].destroyloanscheme('LOAN0003')
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['loanSchemeId'], 'LOAN0001')


    def automatic_update_after_loanscheme_delete_with_delay(self):
        # back to non-default loan scheme and delete scheme with delay
        params = {'loanSchemeId': 'LOAN0004'}
        self.nodes[0].updatevault(self.vaults[1], params)
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['loanSchemeId'], 'LOAN0004')

        destruction_height = self.nodes[0].getblockcount() + 2
        self.nodes[0].destroyloanscheme('LOAN0004', destruction_height)
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['loanSchemeId'], 'LOAN0004')

        # now LOAN0002 is deleted in next block
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['loanSchemeId'], 'LOAN0001')


    def deposittovault_with_invalid_params(self):
        # Insufficient funds
        try:
            self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '101@DFI')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Insufficient funds" in errorString)
        # Check from auth
        try:
            self.nodes[0].deposittovault(self.vaults[0], self.accountBTC, '1@DFI')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Incorrect authorization for {}".format(self.accountBTC) in errorString)
        # Check negative amount
        try:
            self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '-1@DFI')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Amount out of range" in errorString)
        # Check too small amount
        try:
            self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '0.000000001@DFI')
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Invalid amount" in errorString)

    def test_deposittovault(self):
        # Check deposit 1 satoshi
        self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '0.00000001@DFI')
        self.nodes[0].generate(1)
        self.nodes[0].withdrawfromvault(self.vaults[0], self.accountDFI, "0.00000001@DFI")
        self.nodes[0].generate(1)

        self.nodes[1].deposittovault(self.vaults[0], self.accountBTC, '0.7@BTC')
        self.nodes[1].generate(1)
        self.sync_blocks()
        vault = self.nodes[1].getvault(self.vaults[0])
        assert_equal(vault['collateralAmounts'], ['0.70000000@BTC'])
        acBTC = self.nodes[1].getaccount(self.accountBTC)
        assert_equal(acBTC, ['9.30000000@BTC'])

    def takeloan_breaking_50pctDFI_rule(self):
        try:
            self.nodes[0].takeloan({
                    'vaultId': self.vaults[0],
                    'amounts': "0.1@TSLA"})
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("At least 50% of the minimum required collateral must be in DFI when taking a loan" in error_str)

    def takeloan_with_50pctDFI(self):
        self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '0.7@DFI')
        self.nodes[0].generate(1)
        self.sync_blocks()

        vault = self.nodes[1].getvault(self.vaults[0])
        assert_equal(vault['collateralAmounts'], ['0.70000000@DFI', '0.70000000@BTC'])
        acDFI = self.nodes[0].getaccount(self.accountDFI)
        assert_equal(acDFI, ['99.30000000@DFI', '173.20507075@DUSD-DFI', '99.99999000@DUSD-TSLA'])

        self.nodes[0].deposittovault(self.vaults[0], self.accountDFI, '0.3@DFI')
        self.nodes[0].generate(1)
        self.sync_blocks()

        self.nodes[1].deposittovault(self.vaults[0], self.accountBTC, '0.3@BTC')
        self.nodes[1].generate(1)
        self.sync_blocks()

        vault = self.nodes[1].getvault(self.vaults[0])
        assert_equal(vault['collateralAmounts'],['1.00000000@DFI', '1.00000000@BTC'])
        acBTC = self.nodes[1].getaccount(self.accountBTC)
        assert_equal(acBTC, ['9.00000000@BTC'])
        acDFI = self.nodes[0].getaccount(self.accountDFI)
        assert_equal(acDFI, ['99.00000000@DFI', '173.20507075@DUSD-DFI', '99.99999000@DUSD-TSLA'])

        oracle1_prices = [{"currency": "USD", "tokenAmount": "1@DFI"}, {"currency": "USD", "tokenAmount": "1@TSLA"}, {"currency": "USD", "tokenAmount": "1@BTC"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(self.oracles[0], timestamp, oracle1_prices)

        self.nodes[0].generate(1)
        self.sync_blocks()

        self.nodes[0].takeloan({
                    'vaultId': self.vaults[0],
                    'amounts': "0.5@TSLA"})

        self.nodes[0].generate(1)
        self.sync_blocks()

        interest = self.nodes[0].getinterest('LOAN0001')[0]
        assert_equal(interest['interestPerBlock'], Decimal('3E-8'))

        vault = self.nodes[0].getvault(self.vaults[0])
        assert_equal(vault['loanAmounts'], ['0.50000003@TSLA'])
        assert_equal(vault['collateralValue'], Decimal('1.80000000'))
        assert_equal(vault['loanValue'],Decimal('0.50000003'))
        assert_equal(vault['interestValue'],Decimal('0.00000003'))
        assert_equal(vault['interestAmounts'],['0.00000003@TSLA'])

    def withdraw_breaking_50pctDFI_rule(self):
        try:
            self.nodes[0].withdrawfromvault(self.vaults[0], self.accountDFI, "0.8@DFI")
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("At least 50% of the minimum required collateral must be in DFI" in error_str)

    def move_interest_from_old_scheme(self):
        params = {'loanSchemeId':'LOAN000A'}
        self.nodes[0].updatevault(self.vaults[0], params)
        self.nodes[0].generate(1)
        self.sync_blocks()

        # interest is moved out from old scheme
        interest = self.nodes[0].getinterest('LOAN0001')
        assert_equal(len(interest), 0)

    def vault_enter_liquidation_updating_oracle(self):
        oracle_prices = [{"currency": "USD", "tokenAmount": "4@TSLA"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(self.oracles[0], timestamp, oracle_prices)

        self.nodes[0].generate(240)
        self.sync_blocks()
        vault = self.nodes[0].getvault(self.vaults[0])
        assert_equal(vault['state'], "inLiquidation")
        assert_equal(vault['liquidationHeight'], 1560)
        assert_equal(vault['liquidationPenalty'], Decimal('5.00000000'))
        assert_equal(vault['batchCount'], 1)

        assert_raises_rpc_error(-26, 'Vault is under liquidation', self.nodes[0].closevault, self.vaults[0], self.owner_addresses[0])

    def listvaults_state_filtering(self):
        # check listvaults
        list_vault = self.nodes[0].listvaults()
        assert_equal(len(list_vault), 4)

        list_vault = self.nodes[0].listvaults({"state": "active"})
        assert_equal(len(list_vault), 3)

        list_vault = self.nodes[0].listvaults({"state": "inLiquidation"})
        assert_equal(len(list_vault), 1)

    def updatevault_to_scheme_with_lower_collateralization_ratio(self):
        self.nodes[0].deposittovault(self.vaults[1], self.accountDFI, '2.5@DFI')
        self.nodes[0].generate(1)
        self.sync_blocks()

        vault = self.nodes[0].getvault(self.vaults[1])
        assert_equal(vault['collateralAmounts'], ['2.50000000@DFI'])
        assert_equal(self.nodes[0].getaccount(self.owner_addresses[1]), [])

        self.nodes[0].takeloan({
                    'vaultId': self.vaults[1],
                    'amounts': "0.355@TSLA"})
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])
        self.nodes[0].createloanscheme(200, 2.5, 'LOAN0005')
        self.nodes[0].generate(1)
        vault = self.nodes[0].getvault(self.vaults[1])

        params = {'loanSchemeId': 'LOAN0005'}

        try:
            self.nodes[0].updatevault(self.vaults[1], params)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("Vault does not have enough collateralization ratio defined by loan scheme - 176 < 200" in errorString)
        self.nodes[0].generate(1)

    def closevault_with_active_loans(self):
        try:
            self.nodes[0].closevault(self.vaults[1], self.owner_addresses[1])
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Vault <"+self.vaults[1]+"> has loans" in error_str)
        self.nodes[0].generate(1)

    def test_closevault(self):
        list_vault = self.nodes[1].listvaults()
        assert_equal(len(list_vault), 4)
        self.nodes[0].closevault(self.vaults[3], self.owner_addresses[1])
        self.nodes[0].generate(1)
        list_vault = self.nodes[1].listvaults()
        assert_equal(len(list_vault), 3)
        try:
            self.nodes[1].getvault(self.vaults[3])
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Vault <"+self.vaults[3]+"> not found" in error_str)

    def estimatevault_with_invalid_params(self):
        # Invalid loan token
        try:
            self.nodes[0].estimatevault('3.00000000@DFI', '3.00000000@TSLAA')
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Invalid Defi token: TSLAA" in error_str)
        # Invalid collateral token
        try:
            self.nodes[0].estimatevault('3.00000000@DFII', '3.00000000@TSLA')
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Invalid Defi token: DFII" in error_str)
        # Token not set as a collateral
        try:
            self.nodes[0].estimatevault('3.00000000@TSLA', '3.00000000@TSLA')
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Token with id (2) is not a valid collateral!" in error_str)
        # Token not set as loan token
        try:
            self.nodes[0].estimatevault('3.00000000@DFI', '3.00000000@DFI')
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Token with id (0) is not a loan token!" in error_str)

    def test_estimatevault(self):
        vault = self.nodes[0].getvault(self.vaults[1])
        estimatevault = self.nodes[0].estimatevault(vault["collateralAmounts"], vault["loanAmounts"])
        assert_equal(estimatevault["collateralValue"], vault["collateralValue"])
        assert_equal(estimatevault["loanValue"], vault["loanValue"])
        assert_equal(estimatevault["informativeRatio"], vault["informativeRatio"])
        assert_equal(estimatevault["collateralRatio"], vault["collateralRatio"])

    def test_50pctDFI_fresh_vault_takeloan_withdraw(self):
        # Reset price
        oracle_prices = [{"currency": "USD", "tokenAmount": "1@DFI"}, {"currency": "USD", "tokenAmount": "1@TSLA"}, {"currency": "USD", "tokenAmount": "1@BTC"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(self.oracles[0], timestamp, oracle_prices)
        self.nodes[0].generate(240)

        # Deposit collaterals. 50% of BTC
        address = self.nodes[0].getnewaddress()
        self.nodes[0].generate(1)
        self.sync_blocks()
        self.owner_addresses.append(address)
        self.nodes[1].sendtokenstoaddress({}, { address: '1.50@BTC'})
        self.nodes[1].generate(1)
        self.sync_blocks()
        vault_id = self.nodes[0].createvault(address, 'LOAN000A')
        self.vaults.append(vault_id)
        self.nodes[0].generate(1)
        self.sync_blocks()
        self.nodes[0].deposittovault(vault_id, address, '1.25@BTC') # 1.25@BTC as collateral factor 0.8
        self.nodes[0].deposittovault(vault_id, self.accountDFI, '1@DFI')
        self.nodes[0].generate(1)
        self.sync_blocks()
        self.nodes[0].takeloan({
                        'vaultId': vault_id,
                        'amounts': "1@TSLA"
                    })
        self.nodes[0].generate(1)

        self.nodes[0].deposittovault(vault_id, address, '0.2@BTC')
        self.nodes[0].generate(1)

        # Should be able to withdraw extra BTC
        account = self.nodes[0].getaccount(address)
        assert_equal(account, ['0.05000000@BTC', '1.00000000@TSLA'])
        # try withdraw negative amount
        try:
            self.nodes[0].withdrawfromvault(vault_id, address, "-0.00000001@BTC")
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Amount out of range" in error_str)
        # try withdraw too small amount
        try:
            self.nodes[0].withdrawfromvault(vault_id, address, "0.000000001@BTC")
        except JSONRPCException as e:
            error_str = e.error['message']
        assert("Invalid amount" in error_str)
        # try withdraw 1 satoshi
        self.nodes[0].withdrawfromvault(vault_id, address, "0.00000001@BTC")
        self.nodes[0].withdrawfromvault(vault_id, address, "0.09999999@BTC")
        self.nodes[0].generate(1)
        account = self.nodes[0].getaccount(address)
        assert_equal(account, ['0.15000000@BTC', '1.00000000@TSLA'])

    def test_50pctDFI_rule_after_BTC_price_increase(self):
        # BTC triplicates in price
        oracle_prices = [{"currency": "USD", "tokenAmount": "1@DFI"}, {"currency": "USD", "tokenAmount": "1@TSLA"}, {"currency": "USD", "tokenAmount": "3@BTC"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(self.oracles[0], timestamp, oracle_prices)
        self.nodes[0].generate(240)

        # Should be able to withdraw part of BTC after BTC appreciation in price
        self.nodes[0].withdrawfromvault(self.vaults[4], self.owner_addresses[2], "0.5@BTC")
        self.nodes[0].generate(1)

        # Should not be able to withdraw if DFI lower than 50% of collateralized loan value
        try:
            self.nodes[0].withdrawfromvault(self.vaults[4], self.accountDFI, "0.25@DFI")
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("At least 50% of the minimum required collateral must be in DFI" in errorString)

        # Should be able to take 0.10@TSLA and respect 50% DFI ratio
        self.nodes[0].takeloan({
            'vaultId': self.vaults[4],
            'amounts': "0.10@TSLA"
        })
        self.nodes[0].generate(1)

    def overflowed_collateral_value(self):
        address = self.owner_addresses[2]
        vault_id = self.nodes[0].createvault(address, 'LOAN000A')
        self.nodes[0].generate(1)

        self.nodes[0].utxostoaccount({self.accountDFI: "100000000@" + self.symbolDFI})
        self.nodes[0].generate(1)
        self.nodes[0].deposittovault(vault_id, self.accountDFI, "100000000@" + self.symbolDFI)
        self.nodes[0].generate(1)

        self.nodes[0].takeloan({
            'vaultId': vault_id,
            'amounts': "0.5@TSLA"
        })
        self.nodes[0].generate(1)

        oracle1_prices = [{"currency": "USD", "tokenAmount": "9999999999@DFI"}, {"currency": "USD", "tokenAmount": "1@TSLA"}, {"currency": "USD", "tokenAmount": "1@BTC"}]
        timestamp = calendar.timegm(time.gmtime())
        self.nodes[0].setoracledata(self.oracles[0], timestamp, oracle1_prices)
        self.nodes[0].generate(240)

        vault = self.nodes[0].getvault(vault_id)
        assert_equal(vault['collateralValue'], 0) # collateral value overflowed

        # Actions on vault should be blocked
        assert_raises_rpc_error(-32600, 'Value/price too high', self.nodes[0].takeloan, {'vaultId': vault_id,'amounts': "0.5@TSLA"})
        assert_raises_rpc_error(-32600, 'Value/price too high', self.nodes[0].deposittovault, vault_id, self.accountDFI, "1@" + self.symbolDFI)
        assert_raises_rpc_error(-32600, 'Value/price too high', self.nodes[0].withdrawfromvault, vault_id, address, "1@DFI")

        # Should be able to close vault
        self.nodes[0].paybackloan({'vaultId': vault_id, 'from': address, 'amounts': ["1@TSLA"]})
        self.nodes[0].generate(1)
        self.nodes[0].closevault(vault_id, address)
        self.nodes[0].generate(1)

    def close_vault_check_burninfo_and_owner_close_fee_payback(self):
        self.sync_blocks()
        # Save burninfo and balances before create vault
        balance1Before = self.nodes[1].getbalance()
        burninfoBefore = self.nodes[1].getburninfo()

        # Create vault
        owner1 = self.nodes[1].getnewaddress()
        vaultId = self.nodes[1].createvault(owner1)
        self.nodes[1].generate(1)

        # Save burninfo and balances after create vault
        burninfoAfterCreate = self.nodes[1].getburninfo()
        balance1AfterCreate = self.nodes[1].getbalance()

        # Close vault
        self.nodes[1].closevault(vaultId, owner1)
        self.nodes[1].generate(1)

        # Save burninfo and balances after close vault
        account1AfterClose = self.nodes[1].getaccount(owner1)[0]
        burninfoAfterClose = self.nodes[1].getburninfo()

        # checks
        assert_equal(balance1Before-balance1AfterCreate, Decimal('1.00004640')) # ~1 UTXO charged on createvault
        assert_equal(burninfoBefore['feeburn']-burninfoAfterCreate['feeburn'], Decimal('-0.50000000')) # 0.5 DFI burned on createvault
        assert_equal(account1AfterClose, '0.50000000@DFI') # 0.5 DFI returned to owner
        assert_equal(burninfoAfterClose['feeburn'], burninfoAfterCreate['feeburn']) # No more DFI is burned on close vault

    def close_vault_after_update_owner_check_close_fee_payback(self):
        self.sync_blocks()
        owner1 = self.nodes[1].getnewaddress()
        owner2 = self.nodes[0].getnewaddress()

        # Save burninfo and balances before create vault
        balance1Before = self.nodes[1].getbalance()
        burninfoBefore = self.nodes[1].getburninfo()

        # Create vault
        vaultId = self.nodes[1].createvault(owner1)
        self.nodes[1].generate(1)

        # Save burninfo and balances after create vault
        burninfoAfterCreate = self.nodes[1].getburninfo()
        balance1AfterCreate = self.nodes[1].getbalance()

        # Update vault to owner2
        self.nodes[1].updatevault(vaultId, {"ownerAddress": owner2})
        self.nodes[1].generate(1)
        self.sync_blocks()
        vault = self.nodes[0].getvault(vaultId)
        assert_equal(owner2, vault['ownerAddress'])

        # Close vault without auth
        try:
            self.nodes[1].closevault(vaultId, owner1)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Incorrect authorization for' in errorString)

        self.nodes[0].closevault(vaultId, owner1)
        self.nodes[0].generate(1)

        self.sync_blocks()
        # Save burninfo and balances after close vault
        account1AfterClose = self.nodes[1].getaccount(owner1)
        account2AfterClose = self.nodes[1].getaccount(owner2)

        # checks
        assert_equal(balance1Before-balance1AfterCreate, Decimal('1.00003540')) # ~1 UTXO charged on createvault
        assert_equal(account1AfterClose, ['0.50000000@DFI']) # 0.5 DFI returned to owner1
        assert_equal([], account2AfterClose) # close vault called with owner1


    def run_test(self):
        self.setup()
        self.createvault_with_invalid_parameters()
        self.listvaults_and_filtering()
        self.test_feeburn()
        self.getvault_wrong_vault_address()
        self.test_getvault()
        self.updatevault_with_invalid_parameters()
        self.actions_on_vault_with_scheme_to_be_destroyed()
        self.update_vault_scheme()
        self.automatic_update_after_loanscheme_delete()
        self.automatic_update_after_loanscheme_delete_with_delay()
        self.deposittovault_with_invalid_params()
        self.test_deposittovault()
        self.takeloan_breaking_50pctDFI_rule()
        self.takeloan_with_50pctDFI()
        self.withdraw_breaking_50pctDFI_rule()
        self.move_interest_from_old_scheme()
        self.vault_enter_liquidation_updating_oracle()
        self.listvaults_state_filtering()
        self.updatevault_to_scheme_with_lower_collateralization_ratio()
        self.closevault_with_active_loans()
        self.test_closevault()
        self.estimatevault_with_invalid_params()
        self.test_estimatevault()
        self.test_50pctDFI_fresh_vault_takeloan_withdraw()
        self.test_50pctDFI_rule_after_BTC_price_increase()
        self.overflowed_collateral_value()
        self.close_vault_check_burninfo_and_owner_close_fee_payback()
        self.close_vault_after_update_owner_check_close_fee_payback()

if __name__ == '__main__':
    VaultTest().main()
