"""
Hangman Plugin

A hangman game for the BBS.

Commands:
    HANGMAN or HANG - Start new game
    GUESS <letter> - Guess a letter
    WORD <word> - Guess full word
    HINT - Get hint (costs 2 wrong)

Admin:
    ADMIN <pwd> ADDWORD <word> - Add word
    ADMIN <pwd> DELWORD <word> - Remove word  
    ADMIN <pwd> WORDS - List word count
"""

import random
import time
from bbs.plugins.BasePlugin import BasePlugin, PluginContext
from bbs.protocol.CommandRouter import HandlerContext


# Default wordlist
DEFAULT_WORDS = [
    "MESH", "RADIO", "WIFI", "RADAR", "SIGNAL",
    "NODE", "RADIO", "RADAR", "BAUD", "FREQ",
    "POWER", "ANTENNA", "COAX", "GROUND", "BATTERY",
    "SOLAR", "POWER", "CABLE", "TUNER", "RELAY"
]

# Active games: {node_id: game_state}
active_games = {}


class HangmanGame:
    """Represents a hangman game."""
    
    def __init__(self, word, node_id):
        self.word = word.upper()
        self.node_id = node_id
        self.guessed_letters = set()
        self.wrong_guesses = 0
        self.max_wrong = 6
        self.hint_used = False
        self.start_time = int(time.time())
    
    def GuessLetter(self, letter):
        letter = letter.upper()
        if letter in self.guessed_letters:
            return "Already guessed!"
        
        self.guessed_letters.add(letter)
        
        if letter not in self.word:
            self.wrong_guesses += 1
            if self.wrong_guesses >= self.max_wrong:
                return f"LOSE! Word: {self.word}"
            return f"Wrong! {letter} not in word | Wrong:{self.wrong_guesses}/{self.max_wrong}"
        
        # Check if won
        if all(c in self.guessed_letters for c in self.word):
            return f"WIN! Word: {self.word}"
        
        return self.GetDisplay()
    
    def GuessWord(self, word):
        word = word.upper()
        if word == self.word:
            return f"WIN! Word: {self.word}"
        else:
            self.wrong_guesses += 1
            if self.wrong_guesses >= self.max_wrong:
                return f"LOSE! Word: {self.word}"
            return f"Wrong! | Wrong:{self.wrong_guesses}/{self.max_wrong}"
    
    def GetHint(self):
        if self.hint_used:
            return "Hint already used!"
        
        # Find unguessed letters
        unguessed = [c for c in self.word if c not in self.guessed_letters]
        if not unguessed:
            return "No hints needed - you have all letters!"
        
        hint_letter = random.choice(unguessed)
        self.hint_used = True
        self.wrong_guesses += 2  # Cost 2 wrong guesses
        if self.wrong_guesses >= self.max_wrong:
            return f"Hint: {hint_letter} | LOSE! Word: {self.word}"
        return f"Hint: {hint_letter} | Wrong:{self.wrong_guesses}/{self.max_wrong}"
    
    def GetDisplay(self):
        display = []
        for c in self.word:
            if c in self.guessed_letters:
                display.append(c)
            else:
                display.append("_")
        return f"{' '.join(display)} | Wrong:{self.wrong_guesses}/{self.max_wrong}"


def HandleHangmanCommand(context: HandlerContext) -> str:
    """Main handler for hangman commands."""
    args = context.arguments
    
    context.logger.info(f"Hangman args: {args} from {context.from_node}")
    
    # Handle "HANG GUESS X" or "HANG WORD X" format
    # When command is HANG but first arg is a subcommand
    if args and args[0].upper() in ("GUESS", "WORD", "HINT", "STATUS", "QUIT", "ABANDON"):
        # Run the subcommand
        cmd = args[0].upper()
        sub_args = args[1:] if len(args) > 1 else []
        
        # Check for active game for these commands
        if context.from_node not in active_games:
            return "No game. Start: HANG"
        
        game = active_games[context.from_node]
        
        if cmd == "GUESS":
            if not sub_args:
                return "GUESS <letter>"
            letter = sub_args[0]
            result = game.GuessLetter(letter)
            if "WIN" in result or "LOSE" in result:
                del active_games[context.from_node]
            return result
        
        if cmd == "WORD":
            if not sub_args:
                return "WORD <guess>"
            word = sub_args[0]
            result = game.GuessWord(word)
            if "WIN" in result or "LOSE" in result:
                del active_games[context.from_node]
            return result
        
        if cmd == "HINT":
            result = game.GetHint()
            if "WIN" in result or "LOSE" in result:
                del active_games[context.from_node]
            return result
        
        if cmd == "STATUS":
            return game.GetDisplay()
        
        if cmd in ("QUIT", "ABANDON"):
            del active_games[context.from_node]
            return "Game abandoned. New game: HANG"
    
    # Start new game (no args or HANG/HANGMAN command)
    if not args or args[0].upper() in ("HANGMAN", "HANG", "NEW"):
        return StartGame(context)
    
    # Check for active game
    if context.from_node not in active_games:
        return "No game. Start: HANG"
    
    game = active_games[context.from_node]
    
    # Guess letter
    if cmd == "GUESS":
        if len(args) < 2:
            return "GUESS <letter>"
        letter = args[1]
        result = game.GuessLetter(letter)
        if "WIN" in result or "LOSE" in result:
            del active_games[context.from_node]
        return result
    
    # Guess word
    if cmd == "WORD":
        if len(args) < 2:
            return "WORD <guess>"
        word = args[1]
        result = game.GuessWord(word)
        if "WIN" in result or "LOSE" in result:
            del active_games[context.from_node]
        return result
    
    # Hint
    if cmd == "HINT":
        result = game.GetHint()
        if "WIN" in result or "LOSE" in result:
            del active_games[context.from_node]
        return result
    
    # Status
    if cmd == "STATUS":
        return game.GetDisplay()
    
    # Abandon
    if cmd in ("QUIT", "ABANDON", "STOP"):
        del active_games[context.from_node]
        return "Game abandoned. New game: HANG"
    
    return "HANG | GUESS <L> | WORD <w> | HINT"


def StartGame(context: HandlerContext) -> str:
    """Start a new hangman game."""
    # Check if game already exists
    if context.from_node in active_games:
        return f"Game in progress! | {active_games[context.from_node].GetDisplay()}"
    
    # Get word from database or use default
    # HandlerContext uses 'database', PluginContext uses 'Database'
    if hasattr(context, 'database'):
        db = context.database
    else:
        db = context.Database
    
    word = None
    try:
        cursor = db.connection.execute(
            "SELECT word FROM hangman_words ORDER BY RANDOM() LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            word = row['word']
    except Exception as e:
        context.logger.warning(f"Failed to get word from DB: {e}")
    
    if not word:
        word = random.choice(DEFAULT_WORDS)
        context.logger.info(f"Using default word: {word}")
    
    # Create new game
    game = HangmanGame(word, context.from_node)
    active_games[context.from_node] = game
    
    return f"New game! | {game.GetDisplay()}"


class HangmanPlugin(BasePlugin):
    """Hangman game plugin."""
    
    Name = "hangman"
    Version = "1.0.0"
    Description = "Hangman game"
    
    CommandHandlers = {
        "HANGMAN": HandleHangmanCommand,
        "HANG": HandleHangmanCommand,
    }
    
    def OnLoad(self, context: PluginContext) -> None:
        super().OnLoad(context)
        self.CreateTables(context)
        self.LoadDefaultWords(context)
        self.logger.info("Hangman plugin loaded")
    
    def CreateTables(self, db_source) -> None:
        """Create hangman tables if they don't exist."""
        try:
            # Handle both PluginContext and Database objects
            if hasattr(db_source, 'Database'):
                # It's a PluginContext
                conn = db_source.Database.connection
            else:
                # It's a Database object
                conn = db_source.connection
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hangman_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    added_at INTEGER NOT NULL
                )
            """)
            conn.commit()
        except Exception as e:
            self.logger.warning(f"Table creation: {e}")
    
    def LoadDefaultWords(self, db_source) -> None:
        """Load default words if table is empty."""
        try:
            # Handle both PluginContext and Database objects
            if hasattr(db_source, 'Database'):
                # It's a PluginContext
                conn = db_source.Database.connection
            else:
                # It's a Database object
                conn = db_source.connection
            
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM hangman_words"
            )
            row = cursor.fetchone()
            if row['cnt'] == 0:
                now = int(time.time())
                for word in DEFAULT_WORDS:
                    try:
                        conn.execute(
                            "INSERT INTO hangman_words (word, added_at) VALUES (?, ?)",
                            (word, now)
                        )
                    except:
                        pass
                conn.commit()
                self.logger.info("Loaded default words")
        except Exception as e:
            self.logger.warning(f"Default words: {e}")
    
    def Migrate(self, database) -> None:
        """Create tables on migration."""
        self.CreateTables(database)
    
    def GetHelpText(self) -> str:
        return "HANG | GUESS <L> | WORD <w>"


def HandleAdminHangman(context: HandlerContext, args) -> str:
    """Handle admin commands for wordlist."""
    if not args:
        return "ADMIN <pwd> ADDWORD|DELWORD|WORDS"
    
    cmd = args[0].upper()
    args = args[1:]
    
    # HandlerContext uses 'database' (not 'Database')
    db = context.database
    
    if cmd == "ADDWORD":
        if not args:
            return "Usage: ADMIN ADDWORD <word>"
        word = args[0].upper()
        if len(word) < 3:
            return "Word must be 3+ letters"
        try:
            now = int(time.time())
            db.connection.execute(
                "INSERT INTO hangman_words (word, added_at) VALUES (?, ?)",
                (word, now)
            )
            db.connection.commit()
            return f"OK: Added {word}"
        except:
            return f"Error: Word exists"
    
    elif cmd == "DELWORD":
        if not args:
            return "Usage: ADMIN DELWORD <word>"
        word = args[0].upper()
        try:
            db.connection.execute(
                "DELETE FROM hangman_words WHERE word = ?",
                (word,)
            )
            db.connection.commit()
            return f"OK: Deleted {word}"
        except:
            return f"Error: Word not found"
    
    elif cmd == "WORDS":
        try:
            cursor = db.connection.execute(
                "SELECT COUNT(*) as cnt FROM hangman_words"
            )
            row = cursor.fetchone()
            return f"Hangman words: {row['cnt']}"
        except:
            return "Error: Cannot count words"
    
    return "ADMIN <pwd> ADDWORD|DELWORD|WORDS"
