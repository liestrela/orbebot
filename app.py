import asyncio
import requests
import discord as d
from os import environ as env
from subprocess import Popen
from discord.ext import commands
from discord.ext import tasks
from mcrcon import MCRcon as mcr

bot = commands.Bot(command_prefix="!",\
                   intents=d.Intents.all(),
                   help_command=None);

rcon = mcr("localhost", env["RCON_PASS"], port=25575);

ICANHAZIP_URL = "https://ipv4.icanhazip.com";

help_msg = "```!ipwl [ip] - adiciona IPv4 na whitelist\n"\
"!command [comando] - roda comando no servidor (cuidado)\n"\
"!start - abre o servidor\n"\
"!stop - fecha o servidor\n"\
"!status - verifica se o servidor está aberto\n"\
"!ip - retorna o IPv4 do servidor (caso o DNS esteja bichado)\n"\
"!help - essa mensagem```";

def valid_ipv4(addr):
	ps=addr.split(".");
	if len(ps)!=4: return False;
	try: return all(0<=int(p)<256 for p in ps);
	except ValueError: return False;

def srv_status():
	try:
		rcon.connect();
		rcon.disconnect();
		return True;
	except ConnectionRefusedError:
		return False;

async def start_srv(ctx):
	proc = await asyncio.create_subprocess_shell(
		env["MCSRV_PATH"],
		stdout=asyncio.subprocess.PIPE
	);

	while True:
		line = await proc.stdout.readline();
		if not line: break;

		msg = line.decode().strip();
		msg = "```"+msg+"```";
		if msg: await send_channel(int(env["BUF_CHAN"]), msg);

@bot.event
async def on_ready():
	dyn_ipv4.start();
	print(f"Up and running as {bot.user}");

@tasks.loop(seconds=300)
async def dyn_ipv4():
	res = requests.get(env["DYNIP_URL"]);

	if not res.text.startswith("ERROR"):
		await send_channel(int(env["WARN_CHAN"]), \
                           "IPv4 do servidor mudou. "\
                           "Aguarde ~10 minutos para a propagação");

@bot.hybrid_command(name="ipwl")
async def ipwl(ctx, arg):
	if not valid_ipv4(arg):
		await ctx.send("endereço não é um IPv4");
	else:
		try:
			rcon.connect();
			rcon.command(f"ipwl addip {arg}");
			rcon.disconnect();
			await ctx.send(f"{arg} adicionado à whitelist!");
		except ConnectionRefusedError:
			await ctx.send("Servidor indisponível");

@bot.hybrid_command(name="command")
async def command(ctx, *, arg):
	try:
		rcon.connect();
		res = rcon.command(arg);
		rcon.disconnect();
		if res: await ctx.send(f"Servidor: {res}");
	except ConnectionRefusedError:
		await ctx.send("Servidor indisponível");

async def send_channel(chan_id, msg):
	chan = bot.get_channel(chan_id);
	if chan: await chan.send(msg);

@bot.hybrid_command(name="start")
async def start(ctx):
	if srv_status():
		await ctx.send("Servidor já está aberto");
		return;
	else:
		asyncio.create_task(start_srv(ctx));
		await ctx.send("Iniciando (leva alguns segundos)...");

@bot.hybrid_command(name="stop")
async def stop(ctx):
	try:
		rcon.connect();
		res = rcon.command("stop");
		rcon.disconnect();
		if res: await ctx.send(f"Fechando...");
	except ConnectionRefusedError:
		await ctx.send("Servidor já está fechado");

@bot.hybrid_command(name="status")
async def status(ctx):
	if srv_status(): await ctx.send("Servidor aberto");
	else: await ctx.send("Servidor fechado");

@bot.hybrid_command(name="ip")
async def ip(ctx):
	res = await asyncio.to_thread(requests.get, ICANHAZIP_URL);
	await ctx.send(res.text);

@bot.hybrid_command(name="help")
async def help(ctx):
	await ctx.send(help_msg);

@bot.event
async def on_command_error(ctx, err):
	if isinstance(err, commands.MissingRequiredArgument):
		await ctx.send("Argumento faltando");

if __name__ == "__main__":
	bot.run(env["ORBE_TOKEN"]);
