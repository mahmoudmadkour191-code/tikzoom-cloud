<h1 align="center">CC Scraper Telegram Bot</h1>

<p align="center">
  <a href="https://github.com/abirxdhack/CC-Scrapper/stargazers"><img src="https://img.shields.io/github/stars/abirxdhack/CC-Scrapper?color=blue&style=flat" alt="GitHub Repo stars"></a>
  <a href="https://github.com/abirxdhack/CC-Scrapper/issues"><img src="https://img.shields.io/github/issues/abirxdhack/CC-Scrapper" alt="GitHub issues"></a>
  <a href="https://github.com/abirxdhack/CC-Scrapper/pulls"><img src="https://img.shields.io/github/issues-pr/abirxdhack/CC-Scrapper" alt="GitHub pull requests"></a>
  <a href="https://github.com/abirxdhack/CC-Scrapper/graphs/contributors"><img src="https://img.shields.io/github/contributors/abirxdhack/CC-Scrapper?style=flat" alt="GitHub contributors"></a>
  <a href="https://github.com/abirxdhack/CC-Scrapper/network/members"><img src="https://img.shields.io/github/forks/abirxdhack/CC-Scrapper?style=flat" alt="GitHub forks"></a>
</p>

<p align="center">
  <em>CC Scraper: An advanced Telegram bot script to scrape credit cards from specified Telegram groups and channels.</em>
</p>
<hr>

## Features

- Scrapes cards from private/public Telegram groups and channels.
- Supports format: group/channel username, ID, or link.
- Scrapes specific BIN credit cards.
- Removes duplicate credit cards.
- Handles multiple requests at a time.
- Super-fast scraping speed.
- New Feature: Scrape from multiple chats using a single command.
- Join Request Automatically Send Join Request To Chats Which Requires.
- New Libraries Added For Speed Up.
- Fixed UserAlreadyParticipant Error In Joinning And Scrapping From Private Chats.
- Logging Added So That You Can See Every Functions Work In Console.
- Updated All Regex Pattern.
- Bin Filter Updated And Bank Filter Added.
- `user_link` Variable Added For Nice Interface In Caption `CC Scrapped By`
- Scrape Through Chat ID Of Chat Added Example `/scr -1003463745639 10`
- Multiple CC Scrapper Has Some Common Features Of CC Scrapper.

## Requirements

Before you begin, ensure you have met the following requirements:

- Python 3.9 or higher.
- `pyrogram` and `tgcrypto` libraries. ✨Note You Can Also Use `pyrofork`
- A Telegram bot token (you can get one from [@BotFather](https://t.me/BotFather) on Telegram).
- API ID and Hash: You can get these by creating an application on [my.telegram.org](https://my.telegram.org).
- To Get `SESSION_STRING` Open [@ItsSmartToolBot](https://t.me/ItsSmartToolBot). Bot and use /pyro command and then follow all instructions.

## Installation

To install `pyrogram` , `aiofiles` `asyncio` and `tgcrypto`, run the following command:

```bash
pip install -r requirements.txt
```

**Note: If you previously installed `pyrofork`, uninstall it before installing `pyrogram`.**

## Configuration

1. Open the `config.py` file in your favorite text editor.
2. Replace the placeholders for `API_ID`, `API_HASH`, `SESSION_STRING`, `ADMIN_IDS`, `DEFAULT_LIMIT`, `ADMIN_LIMIT` and `BOT_TOKEN` with your actual values:
   - **`API_ID`**: Your API ID from [my.telegram.org](https://my.telegram.org).
   - **`API_HASH`**: Your API Hash from [my.telegram.org](https://my.telegram.org).
   - **`SESSION_STRING`**: The session string generated using [@ItsSmartToolBot](https://t.me/ItsSmartToolBot).
   - **`BOT_TOKEN`**: The token you obtained from [@BotFather](https://t.me/BotFather).

3. **Optional VARS**:
   - **`ADMIN_IDS`**: List of admin user IDs who have elevated permissions.
   - **`ADMIN_LIMIT`**: The maximum number of messages admins can scrape in a single request.
   - **`DEFAULT_LIMIT`**: The maximum number of messages regular users can scrape in a single request.

## Deploy the Bot

```sh
git clone https://github.com/abirxdhack/CC-Scrapper
cd CC-Scrapper
python scrapper.py
```
## Deploy The Bot With Screen

```sh
git clone https://github.com/abirxdhack/CC-Scrapper
cd CC-Scrapper
screen -S CCScrapperBot
python scr.py
```

## Supported Commands

### Single Channel Scrape

1. Use the `/scr` command followed by the group or channel username and the number of messages to scrape.

    ```text
    /scr @channel_username 1000
    ```

2. Optionally, you can scrape any target BIN cards by providing the BIN number.

    ```text
    /scr @channel_username 1000 434769
    ```

3. Optionally, you can scrape messages containing a specific bank name by providing the bank name.

    ```text
    /scr @channel_username 1000 BankName
    ```

4. Use a chat ID instead of the username for private channels:

    ```text
    /scr -1001234567890 1000
    ```

5. Use an invite link for private channels:

    ```text
    /scr https://t.me/+abcdef1234567890 1000
    ```

### Multi Channel Scrape

1. Use the `/mc` command to scrape from multiple chats by specifying multiple usernames and the total number of messages to scrape:

    ```text
    /mc @channel_username @channel_username1 1000
    ```

2. For private channels using chat IDs with the `/mc` command:

    ```text
    /mc -1001234567890 -1009876543210 1000
    ```

3. For private channels using invite links with the `/mc` command:

    ```text
    /mc https://t.me/+abcdef1234567890 https://t.me/+uvwxyz9876543210 1000
    ```

### General Notes

- The `@channel_username` can be replaced with the actual username of the channel or group.
- The `-1001234567890` should be replaced with the actual chat ID of the private channel or group.
- The `https://t.me/+abcdef1234567890` should be replaced with the actual invite link of the private channel or group.
- The `1000` represents the number of messages to scrape and can be adjusted as needed.
- For multi-channel scrape (`/mc`), the last argument should always be the total number of messages to scrape across all specified channels.

## Major Note
**DEFAULT_LIMIT** Currently Set To 5000 Because Request Over 10000 May Cause Your User Acc `Ban Or Logout`
**ADMIN_LIMIT** Currently Set To 10000 Because Request Over 10000 May Cause Your User Acc `Ban Or Logout`

✨ **Notes**:
- Ensure the bot is an administrator in the channels/groups you want to scrape from for the best results.
- The bot can handle a high number of requests simultaneously, but it's a good practice to monitor its performance and adjust limits if necessary.
- If you encounter any issues, check the bot logs for detailed error messages.
- Keep your API credentials and session string secure to prevent unauthorized access to your bot.
- First Clone Repo Then Update Credentials Dont Direct Commit On Github To  Keep Credentials Secure.

## Authors
- Name: Bisnu Ray 
- Telegram: [@TheSmartBisnu](https://t.me/TheSmartBisnu)
## Update Author
- Name: Abir Arafat Chawdhury
- Telegram: [@ModVip_rm](https://t.me/ModVip_rm)

Feel free to reach out if you have any questions or feedback In My Telegram [Abir Arafat Chawdhury](t.me/abirxdhackz) 
