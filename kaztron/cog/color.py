import discord
from discord.ext import commands

from PIL import Image, ImageDraw, ImageFont
import io

from kaztron import errors, KazCog
from kaztron.config import get_kaztron_config
from kaztron.utils.checks import in_channels
from kaztron.utils.logging import message_log_str

def getIfromRGB(red, green, blue):
    RGBint = (red<<16) + (green<<8) + blue
    return RGBint

class ColorCog(KazCog):
    config = get_kaztron_config()
    ch_allowed_list = (
        config.get('color', 'channel_color'),
        config.get("discord", "channel_test"),
        config.get("discord", "channel_output")
    )

    def __init__(self, bot):
        super().__init__(bot)
        self.ch_points = None
        self.base_img = Image.open('data/color_base.png')
        self.font = ImageFont.truetype('data/Whitney_sb.otf', size=17)

    async def on_ready(self):
        self.ch_points= self.bot.get_channel(self.config.get('color', 'channel_color'))
        if self.ch_points is None:
            raise ValueError("Channel {} not found".format(self.config.get('color', 'channel_color')))
        await super().on_ready()
        
    def createImage(self, red, green, blue, name):
        example = self.base_img.copy()
        draw = ImageDraw.Draw(example)
        (x, y) = (0, -2)
        c = 'rgb({},{},{})'.format(red, green, blue)
        
        draw.text((x,y), name, fill=c, font=self.font)
        location = 'data/temp.png'
        example.save(location)
        return location

    @commands.group(invoke_without_command=True, pass_context=True, aliases=['colour, c'])
    async def color(self, ctx: commands.Context, red: int, green: int, blue: int):
        if not isinstance(ctx.message.channel, discord.PrivateChannel):
            await self.bot.say("This is a DM only command. Please DM me to use it.")
            return
        rgb=(red, green, blue)
        if any (c<0 or c>255 for c in rgb):
            await self.bot.say("Values have to be between 0 and 255")
            return
        await self.bot.send_file(ctx.message.channel, self.createImage(red,green,blue,ctx.message.author.name))
    
    @color.command(pass_context=True, ignore_extra=False)
    async def set (self, ctx: commands.Context, red: int, green: int, blue: int):
        if not isinstance(ctx.message.channel, discord.PrivateChannel):
            await self.bot.say("This is a DM only command. Please DM me to use it.")
            return
        if any (c<0 or c>255 for c in rgb):
            await self.bot.say("Values have to be between 0 and 255")
            return
        
        serv = list(self.bot.servers)[0]
        user = serv.get_member(ctx.message.author.id)
        if len(user.roles) > 1:
            for role in reversed(user.roles):
                    if role.color.value != 0:
                        user_role=role
                        break
                        
        await self.bot.edit_role(serv, user_role, color=discord.Color(getIfromRGB(red,green,blue)))
        await self.bot.say("New colour has been assigned.")
        
def setup(bot):
	bot.add_cog(ColorCog(bot))