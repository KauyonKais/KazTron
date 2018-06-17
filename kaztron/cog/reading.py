import discord
from discord.ext import commands
import logging



from kaztron import errors, KazCog
from kaztron.config import get_kaztron_config
from kaztron.utils.checks import in_channels
from kaztron.utils.logging import message_log_str

logger = logging.getLogger(__name__)


class ReadingSession:
    def __init__(self, title):
        self.title=title
    readings=[]

class Reading:
    def __init__(self, reader, content):
        self.content = content
        self.reader = reader
    def __str__(self):
        return "{} reading: {}".format(self.reader.display_name, self.content)
    __repr__ = __str__


class ReadingCog(KazCog):
    config = get_kaztron_config()
    ch_allowed_list = (
        config.get('reading', 'channel_reading'),
        config.get("discord", "channel_test"),
        config.get("discord", "channel_output")
    )
    
    reading_role = config.get('reading', 'role_follow')

    def __init__(self, bot):
        super().__init__(bot)
        self.ch_reading = None
    
    current_session = None

    MAX_DAYS=10
    async def on_ready(self):
        self.ch_reading= self.bot.get_channel(self.config.get('reading', 'channel_reading'))
        if self.ch_reading is None:
            raise ValueError("Channel {} not found".format(self.config.get('reading', 'channel_reading')))

        roleman = self.bot.get_cog("RoleManager")  # type: RoleManager
        if roleman:
            try:
                roleman.add_managed_role(
                    role_name=self.reading_role,
                    join="follow",
                    leave="unfollow",
                    join_msg="You are now assigned the {} role for pings regarding readings or the like.".format(self.reading_role),
                    leave_msg="You are now longer assigned the {} role.".format(self.reading_role),
                    join_err="You already have the {} role! Use `.reading unfollow` if you don't want it.".format(self.reading_role),
                    leave_err="You don't have the {} role! Use `.reading follow` if you want it.".format(self.reading_role),
                    join_doc="Get notified when readings are happening.",
                    leave_doc="Stop getting notifications about readings.\n\n",
                    join_name="join name",
                    leave_name="leave name",
                    group=self.reading,
                    cog_instance=self,
                    ignore_extra=False
                )
            except discord.ClientException:
                logger.warning("`reading follow` command already defined - "
                               "this is OK if client reconnected")
        else:
            err_msg = "Cannot find RoleManager - is it enabled in config?"
            logger.error(err_msg)
            try:
                await self.bot.send_message(self.dest_output, err_msg)
            except discord.HTTPException:
                logger.exception("Error sending error to {}".format(self.dest_output_id))

            
        await super().on_ready()

    @commands.group(invoke_without_command=True, pass_context=True, aliases=['r'])
    async def reading(self, ctx: commands.Context, *, extra: str=None):
        """
        In order to organize reading sessions in voice chat on this server, BunnyBot has a .reading command. 
        Without any extra commands, this will tell you if a reading is currently happening or not. If there is one, you will be able to add your reading/performance to its list.
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        else:
            await self.bot.say("The reading currently going on is \"{}\", with {} readers listed so far.".format(self.current_session.title, len(self.current_session.readings)))
    
    @reading.command(pass_context = True, ignore_extra = False)
    async def start(self, ctx: commands.Context, *,title: str="Getting Hoarse"):
        """
        [title] start a new reading session with an optional title.
        """
        if self.current_session is not None:
            await self.bot.say("There's already the reading \"{}\" running.".format(self.current_session.title))
        else:
            self.current_session = ReadingSession(title)
            await self.bot.say("Reading started.")
        
    @reading.command(pass_context = True, ignore_extra = False)
    async def stop(self, ctx: commands.Context):
        """
        ends the current session.
        """
        if self.current_session is not None:
            await self.bot.say("Reading \"{}\" has been ended.".format(current_session.title))
            self.current_session = None
        else:
            await self.bot.say("There is no reading going on right now.")
            
    @reading.command(pass_context = True, ignore_extra = False, aliases=['add'])
    async def join(self, ctx: commands.Context, *, content: str="Some story"):
        """
        [title] adds your reading/perfomance to the list for the current session. (also .reading add) 
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        else: 
            self.current_session.readings.append(Reading(ctx.message.author, content))
            await self.bot.say("Reading added as #{}".format(len(self.current_session.readings)))
          
    @reading.command(pass_context = True, ignore_extra = False)
    async def leave(self, ctx: commands.Context):
        """
        Deletes all your readings/perfomances from the list (currently buggy, multiple readings by the author might cause issues)
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        else:
            for r in self.current_session.readings:
                if r.reader.id is ctx.message.author.id:
                    await self.bot.say("Removed \"{}\".".format(r))
                    self.current_session.readings.remove(r)
            await self.bot.say("Removed all readings of {}.".format(ctx.message.author.display_name))
    
    @reading.command(pass_context = True, ignore_extra = False)
    async def next(self, ctx: commands.Context):
        """
        Announces the next reading in the list and pings the reader.
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        else:
            if self.current_session.readings:
                current_reading = self.current_session.readings.pop(0)
                await self.bot.say("Next up: {} with \"{}\".\n{} readers left in the list".format(current_reading.reader.mention, current_reading.content, len(self.current_session.readings)))
            else:
                await self.bot.say("There are no more readers in the list.")
                
    @reading.command(pass_context = True, ignore_extra = False)
    async def peek(self, ctx: commands.Context):
        """
        Shows what the next reading and the next reader will be.
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        else:
            if self.current_session.readings:
                next_reading = self.current_session.readings[0]
                await self.bot.say("Next up: {} with \"{}\".\n{} readers left in the list".format(next_reading.reader.display_name, next_reading.content, len(self.current_session.readings)))
            else:
                await self.bot.say("There are no more readers in the list.")
                
    @reading.command(pass_context = True, ignore_extra = False)
    async def list(self, ctx: commands.Context):
        """
        Lists the readings in the current session.
        """
        if self.current_session is None:
            await self.bot.say("No reading is happening at the moment, sorry!")
        elif not self.current_session.readings:
            await self.bot.say("There are no readings in the list")
        else:
            rs = ""
            for idx, r in enumerate(self.current_session.readings, start=1):
                rs = rs+"\n#{}: {}".format(idx, r)
            await self.bot.say(rs)

    weekdays=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    @reading.command(pass_context = True, ignore_extra = False)
    async def planday(self, ctx: commands.Context, day: str, days: int=5):
        """
        Lists days in single messages for planning purposes.
        Takes a day (Mon, Tue, Wed, Thu, Fri, Sat, Sun) and a number as argument.
        Will then list the amount of days starting with the specified day.
        """
        if day.capitalize() not in self.weekdays:
            await self.bot.say("Sorry, I don't know that day.")
            return
        if days > self.MAX_DAYS:
            await self.bot.say("That is too many! Please don't do more than {} days!".format(MAXDAYS))
            return
        if days < 1:
            await self.bot.say("You need at least one day.")
            return
        m = await self.bot.say("Please wait while I set up the votes.")
        d = self.weekdays.index(day)
        for i in range(d, d+days):
            await self.bot.say(self.weekdays[i%7])
        await self.bot.say("Please choose the days you are most likely to be able to make it to a "
                           "reading.")
        print(m)
        await self.bot.delete_message(m)

    @reading.command(pass_context = True, ignore_extra = False)
    async def plantime(self, ctx: commands.Context, desc: str=""):
        """
        Lists times from 12-20+later in 2 hour intervals, optional description.
        """
        if desc:
            await self.bot.say("Times for {}:".format(desc))
        else:
            await self.bot.say("Reading times:")
        for i in range(12, 18, 2):
            await self.bot.say("{}-{}PM EST".format(i, i+2))
        await self.bot.say("Later")


def setup(bot):
    bot.add_cog(ReadingCog(bot))