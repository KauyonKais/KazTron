import discord
from discord.ext import commands

import requests

from kaztron import errors, KazCog
from kaztron.config import get_kaztron_config
from kaztron.utils.checks import in_channels
from kaztron.utils.logging import message_log_str

# Define some constants
google_base = 'https://maps.googleapis.com/maps/api/'
geocode_api = google_base + 'geocode/json'
wunder_key = "7ca646ead4e5d37c"
dev_key = "AIzaSyC_NGVlhUNqgzHGuK0MyNHPkMp4uDRsy5U"

wunder_api = "http://api.wunderground.com/api/{}/forecast/geolookup/conditions/q/{}.json"

def check_status(status):
    """
    A little helper function that checks an API error code and returns a nice message.
    Returns None if no errors found
    """
    if status == 'REQUEST_DENIED':
        return 'The geocode API is off in the Google Developers Console.'
    elif status == 'ZERO_RESULTS':
        return 'No results found.'
    elif status == 'OVER_QUERY_LIMIT':
        return 'The geocode API quota has run out.'
    elif status == 'UNKNOWN_ERROR':
        return 'Unknown Error.'
    elif status == 'INVALID_REQUEST':
        return 'Invalid Request.'
    elif status == 'OK':
        return None
		
def find_location(location):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :return: dict
    """
    params = {"address": location, "key": dev_key}
    

    json = requests.get(geocode_api, params=params).json()
    error = check_status(json['status'])
    if error:
        print(error)

    return json['results'][0]['geometry']['location']

class WeatherCog(KazCog):
    config = get_kaztron_config()
    ch_allowed_list = (
        config.get('weather', 'channel_weather'),
        config.get("discord", "channel_test"),
        config.get("discord", "channel_output")
    )

    def __init__(self, bot):
        super().__init__(bot)
        self.ch_ping = None

    async def on_ready(self):
        self.ch_weather = self.bot.get_channel(self.config.get('weather', 'channel_weather'))
        if self.ch_weather is None:
            raise ValueError("Channel {} not found".format(self.config.get('weather', 'channel_weather')))
        await super().on_ready()

    @commands.command(pass_context=True, ignore_extra=False, aliases=['we'])
    @in_channels(ch_allowed_list)
    async def weather(self, ctx: commands.Context, *, weather: str):
        """
        Give weather a location and it will tell you the current, today's and tomorrow's weather!
        """
        if not wunder_key:
            print ("This command requires a Weather Underground API key.")
        if not dev_key:
            print ("This command requires a Google Developers Console API key.")

        location = weather
    
    # use find_location to get location data from the user input
        try:
            location_data = find_location(location)
        except Error as e:
            print (e)

        formatted_location = "{lat},{lng}".format(**location_data)

        url = wunder_api.format(wunder_key, formatted_location)
        response = requests.get(url).json()

        if response['response'].get('error'):
            print ("{}".format(response['response']['error']['description']))

        forecast_today = response["forecast"]["simpleforecast"]["forecastday"][0]
        forecast_tomorrow = response["forecast"]["simpleforecast"]["forecastday"][1]

    # put all the stuff we want to use in a dictionary for easy formatting of the output
        weather_data = {
            "place": response['current_observation']['display_location']['full'],
            "conditions": response['current_observation']['weather'],
            "temp_f": response['current_observation']['temp_f'],
            "temp_c": response['current_observation']['temp_c'],
            "humidity": response['current_observation']['relative_humidity'],
            "wind_kph": response['current_observation']['wind_kph'],
            "wind_mph": response['current_observation']['wind_mph'],
            "wind_direction": response['current_observation']['wind_dir'],
            "today_conditions": forecast_today['conditions'],
            "today_high_f": forecast_today['high']['fahrenheit'],
            "today_high_c": forecast_today['high']['celsius'],
            "today_low_f": forecast_today['low']['fahrenheit'],
            "today_low_c": forecast_today['low']['celsius'],
            "tomorrow_conditions": forecast_tomorrow['conditions'],
            "tomorrow_high_f": forecast_tomorrow['high']['fahrenheit'],
            "tomorrow_high_c": forecast_tomorrow['high']['celsius'],
            "tomorrow_low_f": forecast_tomorrow['low']['fahrenheit'],
            "tomorrow_low_c": forecast_tomorrow['low']['celsius']
        }

    # Get the more accurate URL if available, if not, get the generic one.
        """if "?query=," in response["current_observation"]['ob_url']:
            weather_data['url'] = web.shorten(response["current_observation"]['forecast_url'])
        else:
            weather_data['url'] = web.shorten(response["current_observation"]['ob_url'])
"""
        current_weather = "{conditions}\n{temp_f}F/{temp_c}C\n{humidity} humidity".format(**weather_data)
        today_weather = "{today_conditions}\nHigh: {today_high_f}F/{today_high_c}C\nLow: {today_low_f}F/{today_low_c}C".format(**weather_data)
        tomorrow_weather = "{tomorrow_conditions}\nHigh: {tomorrow_high_f}F/{tomorrow_high_c}C\nLow: {tomorrow_low_f}F/{tomorrow_low_c}C".format(**weather_data)
        embed=discord.Embed(title=weather_data["place"], description=current_weather)
        embed.add_field(name="Today", value=today_weather, inline=True)
        embed.add_field(name="Tomorrow", value=tomorrow_weather, inline=True)
        embed.set_footer(text=response["current_observation"]['ob_url'])
        await self.bot.say(embed=embed)


def setup(bot):
    bot.add_cog(WeatherCog(bot))