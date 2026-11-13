import ccxt.async_support as ccxt
import asyncio

async def main():
    k = ccxt.kraken({'enableRateLimit': True})
    await k.load_markets()
    eth_pairs = [s for s in k.markets if 'ETH' in s and ('USD' in s or 'USDT' in s)]
    print(eth_pairs[:20])
    await k.close()

asyncio.run(main())