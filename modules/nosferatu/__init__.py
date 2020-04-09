import sys
import discord
import asyncio

from modules.nosferatu.reaction_message import ReactionMessage
from modules.nosferatu.roles import Renfield, Vampire, Hunter
from modules.base import BaseClassPython

import modules.nosferatu.globals as globals
globals.init()

class MainClass(BaseClassPython):
    name = "Nosferatu"
    help_active = True
    help = {
        "description": "Module du jeu Nosferatu",
        "commands": {
            "`{prefix}{command}`": "Démarre une partie de Nosferatu",
            "`{prefix}{command} join`": "Rejoint la partie de Nosferatu",
            "`{prefix}{command} quit`": "Quitte la partie de Nosferatu",
            "`{prefix}{command} start`": "Démarre la partie de Nosferatu (réservé à Renfield)",
            "`{prefix}{command} nominate`": "Nomine un nouveau Renfield pour la partie de Nosferatu (réservé à Renfield). Cette fonction sera faite automatiquement en début de partie",
            "`{prefix}{command} players`": "Affiche les joueurs de la partie de Nosferatu",
        }
    }
    color = 0xff0000
    command_text = "nosferatu"

    def __init__(self, client):
        super().__init__(client)

    #Lancer la partie
    async def command(self, message, args, kwargs):
        if not message.channel.id in globals.games:
            embed = discord.Embed(title = "Démarrage de la partie de Nosferatu",
                                description = "Tapez !nosferatu join pour rejoindre la partie",
                                color = self.color)

            await message.channel.send(embed = embed)

            globals.games[message.channel.id] = {
                "channel": message.channel,
                "players": {
                    message.author.id: Renfield(message.author)
                }, #Dict pour rapidement accéder aux infos
                "order": [], #L'ordre de jeu (liste des id des joueurs, n'inclut pas Renfield)
                "turn": -1, #Le tour en cours (incrémente modulo le nombre de joueurs - Renfield). -1 = pas commencé
                "clock": [ "dawn" ], #Nuits et Aurore
                "library": [], #Morsures, Incantations, Nuits et Journaux
                "stack": [], #Ce qui est passé à Renfield
                "discard": [], #Ce qui est défaussé
                "rituals": [ "mirror", "transfusion", "transfusion", "distortion", "water" ],
                "changed_renfield": False
            }

            for i in range(16):
                globals.games[message.channel.id]["library"].append("bite")

            for i in range(15):
                globals.games[message.channel.id]["library"].append("spell")

            for i in range(18):
                globals.games[message.channel.id]["library"].append("journal")
        else:
            await message.channel.send("Il y a déjà une partie en cours")

    #Rejoindre la partie
    async def com_join(self, message, args, kwargs):
        if message.channel.id in globals.games:
            game = globals.games[message.channel.id]
            if game["turn"] == -1:
                if message.author.id in game["players"]:
                    await message.channel.send("Tu es déjà dans la partie")
                elif len(game["players"]) < 8:
                    await message.channel.send("<@" + str(message.author.id) + "> rejoint la partie")

                    game["players"][message.author.id] = Hunter(message.author)
                else:
                    await message.channel.send("Il y a déjà le nombre maximum de joueurs (8)")
        else:
            await message.channel.send("Il n'y a pas de partie en cours")

    #Quitter la partie
    async def com_quit(self, message, args, kwargs):
        if message.channel.id in globals.games:
            game = globals.games[message.channel.id]
            if game["turn"] == -1:
                if message.author.id in game["players"]:
                    if game["players"][message.author.id].role == "Renfield":
                        await message.channel.send("Tu ne peux pas quitter la partie si tu es Renfield. Utilise %nosferatu nominate pour changer le Renfield")
                    else:
                        await message.channel.send("<@" + str(message.author.id) + "> quitte la partie")

                        del game["players"][message.author.id]
                elif len(game["players"]) < 8:
                    await message.channel.send("Tu n'es pas dans la partie")
        else:
            await message.channel.send("Il n'y a pas de partie en cours")

    #Liste des joueurs
    async def com_players(self, message, args, kwargs):
        if message.channel.id in globals.games:
            embed = discord.Embed(
                title = "Liste des joueurs",
                color = self.color,
                description = "```" + ', '.join([self.client.get_user(x).name + (" (Renfield)" if (y.role == "Renfield") else "") for x, y in globals.games[message.channel.id]["players"].items()]) + "```"
            )
            await message.channel.send(embed = embed)
        else:
            await message.channel.send("Il n'y a pas de partie en cours")

    #Changer de Renfield
    async def com_nominate(self, message, args, kwargs):
        if message.channel.id in globals.games:
            game = globals.games[message.channel.id]
            if game["turn"] == -1:
                if message.author.id in game["players"]:
                    if globals.games[message.channel.id]["players"][message.author.id].role == "Renfield":
                        await message.channel.send(self.client.get_user(message.author.id).name + " va nominer un nouveau Renfield")

                        players = [x for x in game["players"]]

                        async def set_renfield(reactions):
                            #Change de Renfield
                            index = reactions[message.author.id][0]
                            await message.channel.send(self.client.get_user(players[index]).name + " est maitenant Renfield")

                            game["players"][message.author.id] = Hunter(game["players"][message.author.id].user)
                            game["players"][players[index]] = Renfield(game["players"][players[index]].user)

                            game["changed_renfield"] = True

                        async def cond(reactions):
                            return len(reactions[message.author.id]) == 1

                        await ReactionMessage(cond,
                            set_renfield,
                            check = lambda r, u: u.id == message.author.id
                        ).send(message.channel,
                            "Choisis le joueur que tu veux mettre Renfield",
                            "",
                            self.color,
                            [self.client.get_user(x).name for x in game["players"]]
                        )
                    else:
                        await message.channel.send("Tu n'es pas Renfield")
                else:
                    await message.channel.send("Tu n'es pas dans la partie")
        else:
            await message.channel.send("Il n'y a pas de partie en cours")

    #Début de partie + logique des parties (début des fonctions circulaires)
    async def com_start(self, message, args, kwargs):
        if message.channel.id in globals.games:
            game = globals.games[message.channel.id]
            if game["turn"] == -1:
                if game["players"][message.author.id].role == "Renfield":
                    if len(game["players"]) >= 5 or globals.debug:
                        await message.channel.send("Début de partie")

                        if game["changed_renfield"]:
                            game["players"][message.author.id].game_start(game)
                        else:
                            players = [x for x in game["players"]]

                            async def set_renfield(reactions):
                                #Change Renfield
                                index = reactions[message.author.id][0]
                                print(index)
                                print(players[index])
                                print(game["players"][players[index]])
                                await message.channel.send(game["players"][players[index]].user.name + " est maitenant Renfield")

                                game["players"][message.author.id] = Hunter(game["players"][message.author.id].user)
                                game["players"][players[index]] = Renfield(game["players"][players[index]].user)

                                await game["players"][players[index]].game_start(game)

                            async def cond(reactions):
                                return len(reactions[message.author.id]) == 1

                            await ReactionMessage(cond,
                                set_renfield,
                                check = lambda r, u: u.id == message.author.id
                            ).send(message.channel,
                                "Choisis le joueur que tu veux mettre Renfield",
                                "",
                                self.color,
                                [self.client.get_user(x).name for x in game["players"]]
                            )
                    else:
                        await message.channel.send("Il faut au minimum 5 joueurs pour commencer la partie")
                else:
                    await message.channel.send("Tu n'es pas Renfield")
        else:
            await message.channel.send("Il n'y a pas de partie en cours")

    async def com_end(self, message, args, kwargs):
        if message.channel.id in globals.games:
            game = globals.games[message.channel.id]
            if globals.debug:
                await game["players"][message.author.id].end_game(game)


    async def on_reaction_add(self, reaction, user):
        if not user.bot:
            for message in globals.reaction_messages:
                if message.check(reaction, user) and reaction.emoji in message.number_emojis and message.message.id == reaction.message.id:
                    await message.add_reaction(reaction, user)

    async def on_reaction_remove(self, reaction, user):
        if not user.bot:
            for message in globals.reaction_messages:
                if message.check(reaction, user) and reaction.emoji in message.number_emojis and message.message.id == reaction.message.id:
                    await message.remove_reaction(reaction, user)
