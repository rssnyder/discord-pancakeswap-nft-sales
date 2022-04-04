from time import sleep
from os import getenv

from requests import post, get
from discord_webhook import DiscordWebhook, DiscordEmbed
from tinydb import TinyDB, Query


def get_sales(collection: str) -> dict:
    """
    Get recent sales from pancakeswap
    """

    response = post(
        "https://api.thegraph.com/subgraphs/name/pancakeswap/nft-market",
        json={
            "query": f"""query getCollectionActivity {{
                transactions(first: 50, orderBy: timestamp, orderDirection: desc, where:{{ collection: "{collection}" }}) {{                     
                    id             
                    block
                    timestamp
                    askPrice
                    netPrice
                    withBNB
                    buyer {{
                        id
                    }}
                    seller {{
                        id
                    }}
                    nft {{
                        tokenId
                        metadataUrl
                        currentAskPrice
                        currentSeller
                        latestTradedPriceInBNB
                        tradeVolumeBNB
                        totalTrades
                        isTradable
                        updatedAt
                        otherId
                        collection {{
                            id
                        }}
                    }}
                }}
            }}
            """
        },
    )

    response.raise_for_status()

    return response.json().get("data", {}).get("transactions", [])


def get_listings(collection: str) -> dict:
    """
    Get recent listings from pancakeswap
    """

    response = post(
        "https://api.thegraph.com/subgraphs/name/pancakeswap/nft-market",
        json={
            "query": f"""query getCollectionActivity {{
                nfts(first: 50, orderDirection: desc, orderBy: updatedAt, where: {{ collection: "{collection}", isTradable: true }}) {{
                    tokenId
                    metadataUrl
                    currentAskPrice
                    currentSeller
                    latestTradedPriceInBNB
                    tradeVolumeBNB
                    totalTrades
                    isTradable
                    updatedAt
                    otherId
                    collection {{
                        id
                    }}
                    transactionHistory {{
                        id
                        block
                        timestamp
                        askPrice
                        netPrice
                        withBNB
                        buyer {{
                            id
                        }}
                        seller {{
                            id
                        }}
                    }}
                }}
            }}
            """
        },
    )

    response.raise_for_status()

    return response.json().get("data", {}).get("nfts", [])


def bnb_price() -> float:
    """
    Get the current price of BNB
    """
    
    bnb = get("https://api.coingecko.com/api/v3/coins/binancecoin")
    try:
        bnb.raise_for_status()
        return bnb.json()["market_data"]["current_price"]["usd"]
    except:
        return 0.0


if __name__ == "__main__":

    if getenv("SALES_WEBHOOK_URL"):
        sales_db = TinyDB("sales.json")
        sales = Query()

        for sale in get_sales(getenv("COLLECTION")):

            if sales_db.search(sales.id == sale["id"]):
                print("already sent sale")
                continue

            asset = get(
                f"https://nft.pancakeswap.com/api/v1/collections/{getenv('COLLECTION')}/tokens/{sale['nft']['tokenId']}"
            )

            asset.raise_for_status()

            nft = asset.json()["data"]

            for webhook_url in getenv("SALES_WEBHOOK_URL").split(';'):
                webhook = DiscordWebhook(url=webhook_url)

                embed = DiscordEmbed(
                    title=nft["name"],
                    url=f"https://pancakeswap.finance/nfts/collections/{getenv('COLLECTION')}/{sale['nft']['tokenId']}",
                    description=f"{nft['description']}\n\n**A {nft['name'].split(' ')[0]} just got sold!**\n\n**Seller**: {sale['seller']['id']}\n**Buyer**: {sale['buyer']['id']}\n**Price**: {sale['netPrice']}BNB/${float(sale['netPrice']) * bnb_price()}",
                    color="03b2f8",
                )

                embed.set_author(
                    name="NFT Sold",
                    url="https://pancakeswap.finance/",
                    icon_url="https://pancakeswap.finance/images/decorations/phishing-warning-bunny.webp",
                )

                embed.set_image(url=nft["image"]["original"])

                webhook.add_embed(embed)

                response = webhook.execute()

                if response.status_code == 200:
                    sales_db.insert({"id": sale["id"]})
                    print("sent " + sale["id"])

            sleep(5)

    if getenv("LISTINGS_WEBHOOK_URL"):
        listings_db = TinyDB("listings.json")
        listings = Query()

        for listing in get_listings(getenv("COLLECTION")):

            listing['id'] = ';'.join([listing['currentSeller'], listing['tokenId'],  listing['currentAskPrice']])

            if listings_db.search(listings.id == listing["id"]):
                print("already sent listing")
                continue

            asset = get(
                f"https://nft.pancakeswap.com/api/v1/collections/{getenv('COLLECTION')}/tokens/{listing['tokenId']}"
            )

            asset.raise_for_status()

            nft = asset.json()["data"]

            for webhook_url in getenv("LISTINGS_WEBHOOK_URL").split(';'):
                webhook = DiscordWebhook(url=webhook_url)

                embed = DiscordEmbed(
                    title=nft["name"],
                    url=f"https://pancakeswap.finance/nfts/collections/{getenv('COLLECTION')}/{listing['tokenId']}",
                    description=f"{nft['description']}\n\n**A {nft['name'].split(' ')[0]} just got listed!**\n\n**Seller**: {listing['currentSeller']}\n**Price**: {listing['currentAskPrice']}BNB/${float(listing['currentAskPrice']) * bnb_price()}",
                    color="03b2f8",
                )

                embed.set_author(
                    name="NFT Listed",
                    url="https://pancakeswap.finance/",
                    icon_url="https://pancakeswap.finance/images/decorations/phishing-warning-bunny.webp",
                )

                embed.set_image(url=nft["image"]["original"])

                webhook.add_embed(embed)

                response = webhook.execute()

                if response.status_code == 200:
                    listings_db.insert({"id": listing["id"]})
                    print("sent " + listing["id"])

            sleep(5)
