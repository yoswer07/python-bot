from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, CallbackQuery
import pyromod
import sqlite3


# Se crea un cliente con los datos de la api y el token del bot previamente, este se guarda en un archivo .session
app = Client("my_bot")
con = sqlite3.connect("main.db")
curs = con.cursor()

#Variable para los botones de inicio
start_buttons = [
    [
        InlineKeyboardButton("Animes", callback_data="ANIMES"),
        InlineKeyboardButton("Borrar", callback_data="BORRAR")
    ]
]

#Iniciamos la base de datos
@app.on_message(filters.command('start') & filters.private)
async def start(bot, msg):
    sql = "CREATE TABLE IF NOT EXISTS usuarios(id INT, PRIMARY KEY(id))"
    curs.execute(sql)
    await bot.send_message(msg.chat.id, 'Bienvenido :D')

#Configuramos el menu
@app.on_message(filters.command('menu'))
async def menu(bot, msg):
    username = msg.from_user.username
    text = f"¿En que podemos ayudarte {username}?"
    await msg.reply_text(text=text, reply_markup= InlineKeyboardMarkup(start_buttons))

@app.on_callback_query()
async def callback_query(bot, CallbackQuery):
    username = CallbackQuery.from_user.username
    id = CallbackQuery.from_user.id
    registro = lista_anime(bot, CallbackQuery)
    if CallbackQuery.data == "ANIMES":
        TEXT = f"Estos son tus animes agregados {username}"
        ANIME_BUTTON = []
        for a in registro:
            corto = ''.join(a)
            corto = corto[:25]
            ANIME_BUTTON.append([InlineKeyboardButton(corto, callback_data=corto)])
        await CallbackQuery.edit_message_text(
            TEXT,
            reply_markup = InlineKeyboardMarkup(ANIME_BUTTON)
        )
    for x in registro:
        b = ''.join(x)
        corto = b[:25]
        curs.execute("SELECT nombre_episodio FROM episodios_animes WHERE idanimes = (?) ORDER BY nombre_episodio", (b,))
        registro = curs.fetchall()
        if CallbackQuery.data == corto:
            BOTON_EPISODIO = []
            for episodio in registro:
                corto = ''.join(episodio)
                corto = corto[:25]
                BOTON_EPISODIO.append([InlineKeyboardButton(corto, callback_data=corto)])
            TEXT= f"Elija su episodio {username}"
            await CallbackQuery.edit_message_text(
            TEXT,
            reply_markup = InlineKeyboardMarkup(BOTON_EPISODIO)
            )
        for c in registro:
            d = ''.join(c)
            corto = d[:25]
            curs.execute("SELECT id FROM episodios_animes WHERE nombre_episodio = (?)", (d,))
            registro = curs.fetchone()
            id_anime = ''.join(registro)
            if CallbackQuery.data == corto:
                await sendvid(bot, id, id_anime)
    registro = lista_anime(bot, CallbackQuery)
    if CallbackQuery.data == "BORRAR":
        TEXT = f"Estos son tus animes agregados {username}"
        BORRAR_BUTTON = []
        for a in registro:
            corto = ''.join(a)
            corto = corto[:25]
            BORRAR_BUTTON.append([InlineKeyboardButton(corto, callback_data='BORRAR'+corto)])
        await CallbackQuery.edit_message_text(
            TEXT,
            reply_markup = InlineKeyboardMarkup(BORRAR_BUTTON)
        )
    for x in registro:
        b = ''.join(x)
        corto = b[:25]
        curs.execute("SELECT nombre FROM animes WHERE nombre = (?) ORDER BY nombre", (b,))
        registro = curs.fetchone()
        if CallbackQuery.data == 'BORRAR'+corto:
            curs.execute("DELETE FROM usuario_animes WHERE nombreanime = (?) AND idusuario = (?)", (b, int(id),))
            con.commit()
            await CallbackQuery.edit_message_text(f"Su anime {b} fue borrado exitosamente")

#Creo una carpeta con id unico para guardar los ids de los videos en carpetas clasificadas
@app.on_message(filters.command('archive'))
async def archive(bot,msg):
    id = msg.from_user.id
    curs.execute("SELECT * FROM usuarios WHERE id = (?)", (int(id),))
    registro = curs.fetchall()
    if registro:
        await msg.reply("Ya su carpeta existe :D")
    else:
        curs.execute("INSERT INTO usuarios VALUES ((?))", (int(id),))
        con.commit()
        await msg.reply("Su carpeta a sido creado como Anime-{}".format(id))

#Al recibir un video revisa tanto el metodo de clasificacion como el usuario en la base de datos
@app.on_message(filters.video)
async def cadena(bot, msg):
    id = msg.from_user.id
    curs.execute("SELECT * FROM usuarios WHERE id = (?)", (int(id),))
    registro = curs.fetchall()
    if registro:
        vid = msg.video.file_id
        vid_name = msg.video.file_name
        vid_cap = str(msg.caption)
        sql = "CREATE TABLE IF NOT EXISTS animes(nombre TEXT, PRIMARY KEY(nombre))"
        curs.execute(sql)
        if vid_cap.find('#') > -1:
            for i in msg.caption_entities:
                if str(i.type) == "MessageEntityType.HASHTAG":
                    indice = i.offset
                    largo = i.length
                    nombre_anime = msg.caption[indice + 1: indice + largo]
                    await crear_usuario_anime(nombre_anime, msg, id, vid_name, vid, bot)
        else:
            nombre_man = await msg.chat.ask('*Por favor, ingrese el nombre del anime en formato Pascal_Case*', parse_mode=enums.ParseMode.MARKDOWN)
            await nombre_man.request.edit_text("Nombre Recibido")
            await crear_usuario_anime(nombre_man.text, msg, id, vid_name, vid, bot)
    else:
        await msg.reply("Por favor cree su carpeta unica con el comando /archive")


async def crear_usuario_anime(nombre_anime, msg, id, vid_name, vid, bot):
    await borrar_video(bot, msg)
    sql = """
    CREATE TABLE IF NOT EXISTS usuario_animes(
    idusuario INT,
    nombreanime TEXT,
    PRIMARY KEY(idusuario, nombreanime),
    CONSTRAINT FK_usuario_anime FOREIGN KEY(idusuario) REFERENCES usuarios(id),
    CONSTRAINT FK_anime_usuario FOREIGN KEY(nombreanime) REFERENCES animes(nombres)
    )
    """
    curs.execute(sql)
    curs.execute("SELECT * FROM animes WHERE nombre = (?)", (nombre_anime,))
    registro = curs.fetchall()
    if not registro:
        curs.execute("INSERT INTO animes VALUES ((?))", (nombre_anime,))
        con.commit()
        await msg.reply("Su anime fue registrado")
    else:
        await msg.reply("Veo que quieres agregar más episodios *o*")
    curs.execute("SELECT * FROM usuario_animes WHERE idusuario = (?) AND nombreanime = (?)", (int(id), nombre_anime,))
    registro = curs.fetchall()
    if not registro:
        curs.execute("INSERT INTO usuario_animes VALUES ((?), (?))", (int(id), nombre_anime,))
        con.commit()
        await msg.reply("Estamos trabajando en ello")
    sql = """
    CREATE TABLE IF NOT EXISTS episodios_animes(
    nombre_episodio TEXT,
    id TEXT,
    idanimes TEXT,
    PRIMARY KEY(id),
    CONSTRAINT FK_episodio_anime FOREIGN KEY(idanimes) REFERENCES animes(nombre)
    )
    """
    curs.execute(sql)
    curs.execute("SELECT * FROM episodios_animes WHERE nombre_episodio = (?)", (vid_name,))
    registro = curs.fetchall()
    if registro:
        await msg.reply("El episodio ya se encuentra en nuestra base de datos")
    else:
        curs.execute("INSERT INTO episodios_animes VALUES ((?), (?), (?))", (vid_name, vid, nombre_anime,))
        con.commit()
        await msg.reply("El episodio fue registrado")

#Borramos los videos mandados
async def borrar_video(bot, msg):
    await bot.delete_messages(msg.chat.id, msg.id)

#Enviamos el video solicitado
async def sendvid(bot, id, vid):
    await bot.send_video(id, vid)

#Creamos los botones dependiendo de la base de datos
def lista_anime(bot, msg):
    id = msg.from_user.id
    curs.execute("SELECT nombreanime FROM usuario_animes WHERE idusuario = (?) ORDER BY nombreanime", (int(id),))
    registro = curs.fetchall()
    return (registro)

#Borramos mensaje respondido con el comando /visto
@app.on_message(filters.command('visto'))
async def visto(bot, msg):
    await msg.delete()
    await bot.delete_messages(msg.chat.id, msg.reply_to_message_id)

print("Funcionando")
app.run()        