#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""Test token's RPC.

- verify basic token's creation, destruction, revert, collateral locking
"""

from test_framework.test_framework import DefiTestFramework
from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal
from decimal import Decimal

class PoolPairTest (DefiTestFramework):
    def set_test_params(self):
        self.FCH_HEIGHT = 170
        self.LP_DAILY_DFI_REWARD = 10
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.extra_args = [
                ['-txnotokens=0', '-amkheight=50', '-bayfrontheight=50', '-bayfrontgardensheight=0', '-dakotaheight=160', '-fortcanningheight=163', '-fortcanninghillheight='+str(self.FCH_HEIGHT), '-simulatemainnet', '-jellyfish_regtest=1']
            ]

    def create_tokens(self):
        self.symbolGOLD = "GOLD"
        self.symbolSILVER = "SILVER"
        self.symbolDOGE = "DOGE"

        self.account0 = self.nodes[0].get_genesis_keys().ownerAuthAddress
        self.nodes[0].createtoken({
            "symbol": self.symbolGOLD,
            "name": "Gold token",
            "collateralAddress": self.account0
        })
        self.nodes[0].generate(1)
        self.nodes[0].createtoken({
            "symbol": self.symbolSILVER,
            "name": "Silver token",
            "collateralAddress": self.account0
        })
        self.nodes[0].generate(1)
        self.nodes[0].createtoken({
            "symbol": self.symbolDOGE,
            "name": "DOGE token",
            "collateralAddress": self.account0
        })
        self.nodes[0].generate(1)
        self.symbol_key_GOLD = "GOLD#" + str(self.get_id_token(self.symbolGOLD))
        self.symbol_key_SILVER = "SILVER#" + str(self.get_id_token(self.symbolSILVER))
        self.symbol_key_DOGE = "DOGE#" + str(self.get_id_token(self.symbolDOGE))

    def mint_tokens(self):
        self.nodes[0].minttokens("2000000@" + self.symbol_key_GOLD)
        self.nodes[0].minttokens("3000000@" + self.symbol_key_SILVER)
        self.nodes[0].minttokens("2000000@" + self.symbol_key_DOGE)
        self.account_gs = self.nodes[0].getnewaddress("")
        self.account_sd = self.nodes[0].getnewaddress("")
        self.account_gold = self.nodes[0].getnewaddress("")
        self.account_silver = self.nodes[0].getnewaddress("")
        self.account_doge = self.nodes[0].getnewaddress("")
        self.nodes[0].generate(1)
        self.nodes[0].accounttoaccount(self.account0, {self.account_gs: "1000000@" + self.symbol_key_GOLD})
        self.nodes[0].accounttoaccount(self.account0, {self.account_gs: "1000000@" + self.symbol_key_SILVER})
        self.nodes[0].generate(1)
        self.nodes[0].accounttoaccount(self.account0, {self.account_sd: "1000000@" + self.symbol_key_SILVER})
        self.nodes[0].accounttoaccount(self.account0, {self.account_sd: "1000000@" + self.symbol_key_DOGE})
        self.nodes[0].generate(1)
        self.nodes[0].accounttoaccount(self.account0, {self.account_gold: "1000000@" + self.symbol_key_GOLD})
        self.nodes[0].accounttoaccount(self.account0, {self.account_silver: "1000000@" + self.symbol_key_SILVER})
        self.nodes[0].accounttoaccount(self.account0, {self.account_doge: "1000000@" + self.symbol_key_DOGE})
        self.nodes[0].generate(1)

    def create_pool_pairs(self):
        self.owner = self.nodes[0].getnewaddress("", "legacy")
        self.nodes[0].createpoolpair({
            "tokenA": self.symbol_key_GOLD,
            "tokenB": self.symbol_key_SILVER,
            "commission": 0.01,
            "status": True,
            "ownerAddress": self.owner,
            "pairSymbol": "GS",
        }, [])
        self.nodes[0].generate(1)
        self.nodes[0].createpoolpair({
            "tokenA": self.symbol_key_SILVER,
            "tokenB": self.symbol_key_DOGE,
            "commission": 0.05,
            "status": True,
            "ownerAddress": self.owner,
            "pairSymbol": "SD",
        }, [])
        self.nodes[0].generate(1)

    def add_liquidity(self):
        self.nodes[0].addpoolliquidity({
            self.account_gs: ["1000000@" + self.symbol_key_GOLD, "1000000@" + self.symbol_key_SILVER]
        }, self.account_gs, [])
        self.nodes[0].addpoolliquidity({
            self.account_sd: ["1000000@" + self.symbol_key_DOGE, "1000000@" + self.symbol_key_SILVER]
        }, self.account_sd, [])
        self.nodes[0].generate(1)

    def setup(self):
        self.nodes[0].generate(self.FCH_HEIGHT)
        self.create_tokens()
        self.mint_tokens()
        self.create_pool_pairs()
        self.add_liquidity()

    def test_swap_with_wrong_amounts(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['1000000.00000000@GOLD#128'])
        # try swap negative amount
        try:
            self.nodes[0].poolswap({
                "from": self.account_gs,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": Decimal('-0.00000001'),
                "to": to_address,
                "tokenTo": self.symbol_key_SILVER,
            },[])
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Amount out of range' in errorString)

        #try swap too small amount
        try:
            self.nodes[0].poolswap({
                "from": self.account_gs,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": Decimal('0.000000001'),
                "to": to_address,
                "tokenTo": self.symbol_key_SILVER,
            },[])
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Invalid amount' in errorString)


    def test_simple_swap_1Satoshi(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['1000000.00000000@GOLD#128'])

        self.nodes[0].poolswap({
            "from": self.account_gold,
            "tokenFrom": self.symbol_key_GOLD,
            "amountFrom": 0.00000001,
            "to": to_address,
            "tokenTo": self.symbol_key_SILVER,
        },[])
        self.nodes[0].generate(1)
        from_account = self.nodes[0].getaccount(from_address)
        to_account = self.nodes[0].getaccount(to_address)
        assert_equal(from_account, ['999999.99999999@GOLD#128'])
        assert_equal(to_account, [])

    def test_200_simple_swaps_1Satoshi(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['999999.99999999@GOLD#128'])

        for _ in range(200):
            self.nodes[0].poolswap({
                "from": from_address,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": 0.00000001,
                "to": to_address,
                "tokenTo": self.symbol_key_SILVER,
            },[])
        self.nodes[0].generate(1)
        from_account = self.nodes[0].getaccount(from_address)
        to_account = self.nodes[0].getaccount(to_address)
        assert_equal(from_account, ['999999.99999799@GOLD#128'])
        assert_equal(to_account, [])

    def test_compositeswap_1Satoshi(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['999999.99999799@GOLD#128'])

        testPoolSwapRes =  self.nodes[0].testpoolswap({
            "from": from_address,
            "tokenFrom": self.symbol_key_GOLD,
            "amountFrom": 0.00000001,
            "to": to_address,
            "tokenTo": self.symbol_key_DOGE,
        }, "auto", True)
        assert_equal(testPoolSwapRes["amount"], '0.00000000@130')
        assert_equal(len(testPoolSwapRes["pools"]), 2)

        self.nodes[0].compositeswap({
            "from": from_address,
            "tokenFrom": self.symbol_key_GOLD,
            "amountFrom": 0.00000001,
            "to": to_address,
            "tokenTo": self.symbol_key_DOGE,
        },[])
        self.nodes[0].generate(1)
        from_account = self.nodes[0].getaccount(from_address)
        to_account = self.nodes[0].getaccount(to_address)
        assert_equal(from_account, ['999999.99999798@GOLD#128'])
        assert_equal(to_account, [])

    def test_200_compositeswaps_1Satoshi(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['999999.99999798@GOLD#128'])

        for _ in range(200):
            testPoolSwapRes = self.nodes[0].testpoolswap({
                "from": from_address,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": 0.00000001,
                "to": to_address,
                "tokenTo": self.symbol_key_DOGE,
            }, "auto", True)
            assert_equal(testPoolSwapRes["amount"], '0.00000000@130')
            assert_equal(len(testPoolSwapRes["pools"]), 2)

            self.nodes[0].compositeswap({
                "from": from_address,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": 0.00000001,
                "to": to_address,
                "tokenTo": self.symbol_key_DOGE,
            },[])
        self.nodes[0].generate(1)
        from_account = self.nodes[0].getaccount(from_address)
        to_account = self.nodes[0].getaccount(to_address)
        assert_equal(from_account, ['999999.99999598@GOLD#128'])
        assert_equal(to_account, [])

    def test_negative_swap(self):
        from_address = self.account_gold
        from_account = self.nodes[0].getaccount(from_address)
        to_address = self.nodes[0].getnewaddress("")
        assert_equal(from_account, ['999999.99999598@GOLD#128'])

        try:
            self.nodes[0].testpoolswap({
                "from": from_address,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": -0.00000001,
                "to": to_address,
                "tokenTo": self.symbol_key_DOGE,
            }, "auto", True)
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Amount out of range' in errorString)

        try:
            self.nodes[0].compositeswap({
                "from": from_address,
                "tokenFrom": self.symbol_key_GOLD,
                "amountFrom": -0.00000001,
                "to": to_address,
                "tokenTo": self.symbol_key_DOGE,
            },[])
        except JSONRPCException as e:
            errorString = e.error['message']
        assert('Amount out of range' in errorString)

    def test_poolpair_rewards_before_gov_var_set(self):
        self.nodes[0].generate(120)
        self.nodes[0].setgov({ "LP_DAILY_DFI_REWARD": self.LP_DAILY_DFI_REWARD })
        self.nodes[0].generate(1)

    def run_test(self):
        self.setup()

        self.test_swap_with_wrong_amounts()
        self.test_simple_swap_1Satoshi()
        self.test_200_simple_swaps_1Satoshi()
        self.test_compositeswap_1Satoshi()
        self.test_200_compositeswaps_1Satoshi()
        self.test_negative_swap()

        self.test_poolpair_rewards_before_gov_var_set()


if __name__ == '__main__':
    PoolPairTest ().main ()
