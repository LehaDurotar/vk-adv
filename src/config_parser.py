import json


class Config:
    with open('config.json', 'r') as f:
        config = json.load(f)
        token = config["vk_api"]["access_token"]
        client_id = int(config["vk_api"]["client_id"])
        user_id = config["vk_api"]["user_id"]
        test_public_id = config["vk_api"]["test_public_id"]
        tg_api_token = config["telegram"]["api_token"]
        tg_api_hash = config["telegram"]["api_hash"]
        tg_api_id = int(config["telegram"]["api_id"])
