from util import CredentialsManager
from modules.PodcastCompiler import SpotifyPlaylistCompiler
from modules.LibraryDownloader import Downloader


SpotifyCredentialsFile = "./datafiles/SpotifyCredentials.txt"
CompilerDataFile = "./datafiles/compilerData.txt"

def runDownloader():
  # get the client credentials
  hasCreds, clientId, clientSecret = CredentialsManager.getSpotifyCredentials(SpotifyCredentialsFile)
  
  # check if the crednetials were retrieved successfully
  if not hasCreds:
    print("Could not load spotify credentials from", SpotifyCredentialsFile)

  dl = Downloader( clientId, clientSecret, "output/downloader/")
  dl.downloadFullLibrary( True )

def runCompiler():
  # get the client credentials
  success, clientId, clientSecret = CredentialsManager.getSpotifyCredentials(SpotifyCredentialsFile)
  
  # check if the crednetials were retrieved successfully
  if not success:
    print("Could not load spotify credentials from", SpotifyCredentialsFile)
    
  # instantiate the class
  pc = SpotifyPlaylistCompiler(CompilerDataFile, clientId, clientSecret)

  # add podcasts to playlist
  pc.addAllPodcastsToPlaylist()
  
  # update and save the datafile
  pc.updateDataFile()


def main():
  print("Which module would you like to use?")
  print("1: Spotify Downloader (Offline your entire spotify library)")
  print("2: Podcast Compiler (Add all your podcasts to one playlist)")
  
  choice = input()
  
  while not choice.isdecimal():
    choice = input("Please enter a number:")
    
  choice = int( choice )
  
  match choice:
    case 1:
      runDownloader()
    case 2:
      runCompiler()


def test():
  runDownloader()
  

main()