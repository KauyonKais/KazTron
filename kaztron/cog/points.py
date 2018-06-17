import discord
from discord.ext import commands

import json

from kaztron import errors, KazCog
from kaztron.config import get_kaztron_config
from kaztron.utils.checks import in_channels
from kaztron.utils.logging import message_log_str


class Value:
    def __init__(self, pos, neg):
        self.pos = pos
        self.neg = neg
    def value(self):
        return self.pos-self.neg;
    def string(self):
        return '({}/-{})'.format(self.pos, self.neg)
        
def jdefault(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__

class PointsCog(KazCog):
    config = get_kaztron_config()
    ch_allowed_list = (
        config.get('points', 'channel_points'),
        config.get("discord", "channel_test"),
        config.get("discord", "channel_output")
    )
    point_dict={}

    def __init__(self, bot):
        super().__init__(bot)
        self.ch_points = None
        with open('data/points.dict','r') as dict:
            try:
                self.point_dict = json.load(dict)
            except json.decoder.JSONDecodeError:
                pass
            for key in self.point_dict:
                self.point_dict[key]=Value(self.point_dict[key]['pos'], self.point_dict[key]['neg'])
        dict.close()

    async def on_ready(self):
        self.ch_points= self.bot.get_channel(self.config.get('points', 'channel_points'))
        if self.ch_points is None:
            raise ValueError("Channel {} not found".format(self.config.get('points', 'channel_points')))
        await super().on_ready()

    async def on_message(self, message):
        if isinstance(message.channel, discord.PrivateChannel) or message.author.id==self.bot.user.id:
            return
        s = message.content.strip()

        if s.endswith("++"):
            s=s[:-2].strip().lower()
            if s in self.point_dict.keys():
                self.point_dict[s].pos = self.point_dict[s].pos+1
            else:
                self.point_dict[s] = Value(1,0)
            with open('data/points.dict','w') as dict:
                json.dump(self.point_dict, dict, default=jdefault)
            dict.close()
        elif s.endswith("--"):
            s=s[:-2].strip().lower()
            if s in self.point_dict.keys():
                self.point_dict[s].neg = self.point_dict[s].neg+1
            else:
                self.point_dict[s]= Value(0,1)
            with open('data/points.dict','w') as dict:
                json.dump(self.point_dict, dict, default=jdefault)
            dict.close()

    @commands.command(pass_context=True, ignore_extra=False, aliases=['p'])
    @in_channels(ch_allowed_list)
    async def points(self, ctx, *, points: str):
        """
        A ++ or -- at the end of a message will give the content of that message a point. These points can be read by using .points [target]
        """
        points=points.strip().lower()
        if points in self.point_dict.keys():
            await self.bot.say('Points for *{}*: {} {}'.format(points.title(), self.point_dict[points].value(),self.point_dict[points].string()))
        else:
            await self.bot.say('I do not know *'+points+'*')

def setup(bot):
	bot.add_cog(PointsCog(bot))