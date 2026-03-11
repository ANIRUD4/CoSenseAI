from duckduckgo_search import DDGS

def test_ddgs():
    print("Testing DDGS...")
    try:
        results = DDGS().images(
            keywords="coffee mug",
            region="us-en",
            safesearch="off",
            max_results=5,
        )
        print(f"Found {len(results)} images.")
        for r in results:
            print(r["image"])
    except Exception as e:
        print(f"DDGS Error: {e}")

if __name__ == "__main__":
    test_ddgs()
