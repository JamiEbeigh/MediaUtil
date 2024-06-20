from modules.PodcastCompiler import SpotifyPlaylistCompiler
from modules.LibraryDownloader import Downloader
from util.UtilOptions import UtilOptions

CompilerDataFile = "./dataFiles/compilerData.txt"
optionsFile = "./dataFiles/options.txt"

def runDownloader( options ):
  dl = Downloader(options)
  dl.downloadFullLibrary( True )

def runCompiler(options ):
  # instantiate the class
  pc = SpotifyPlaylistCompiler(CompilerDataFile, options.spotifyClientId, options.spotifyClientSecret)

  # add podcasts to playlist
  pc.addAllPodcastsToPlaylist()
  
  # update and save the datafile
  pc.updateDataFile()

def runMkvConvert(options):
  pass


def main():
  options = UtilOptions(optionsFile)
  
  print("Which module would you like to use?")
  print("1: Spotify Downloader (Offline your entire spotify library)")
  print("2: Podcast Compiler (Add all your podcasts to one playlist)")
  print("3: MKV Converter (Convert MKV files to MP4)")
  
  choice = input()
  
  while not choice.isdecimal():
    choice = input("Please enter a number:")
    
  choice = int( choice )
  
  match choice:
    case 1:
      runDownloader(options)
    case 2:
      runCompiler(options)
    case 3:
      runMkvConvert(options)


def test():
  runDownloader()
  

main()