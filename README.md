# SpotiUtil
A command line tool to complete various tasks using the Spotify API

## Developer note:
I've decided to drastically broaden the scope of this application and as a result, 
this repository is no longer maintained. Instead, I am rebuilding the project with 
a whole host of new features that will be geared more towards managing a home media
server; think Plex, but less bloated. Some of the features in this project may be 
moved to my personal site (also not currently public), but for more info on this 
project specifically you can check out my [MediaUtil2 repository](https://github.com/JamiEbeigh/mediautil2). 

## Prerequisites
* **Python** (I did my testing with version 3.11)
* **Git** (or some method of cloning the repo)
* **MacOs/Linux** 
  * This program *will run on windows*, you do not *need* a unix system
  * This tutorial was written with the asumption that you're using a 
    unix-based operating system. 
  * I'll update it to include instructions for windows whenever I have the time.

## Installation
This can be done in a number of ways, but I'm going to explain it using the 
least amount of third-party software possible. If you've done this before it
might seem like I'm over-explaining a basic git clone, that's because this 
tutorial is aimed at people who are unfamiliar with software development. 

### Step 1: Install Prerequisits
Install Python - this was tested with python 3.11, this command will 
install that version 

```commandline
sudo apt-get update
sudo apt-get install python3.11
```

Install Git
```commandline
sudo apt install git-all
```

### Step 2: Clone the git repository
Navigate to the directory where you would like to store the project files

```commandline
cd /path/to/your/directory/
```

Make sure that you have Git installed 

```commandline
sudo apt-get install git
```

Clone the git repo

```commandline
git clone https://github.com/JamiEbeigh/SpotiUtil.git
```

This project imports another project of mine (a fork of 
[youtube-search-python](https://github.com/alexmercerind/youtube-search-python)) 
as a submodule. There's a chance that it wasn't added when cloning the repo, 
so to ensure that it is added, run:

```commandline
git submodule init
git submodule update
```

### Step 3: Install Python Requirements

Install Python Venv, create a virtual environment, then activate it

```commandline
python3 -m pip install virtualenv
python3 -m venv virtualEnv
source virtualEnv/bin/activate
```

Install requirements.txt

```commandline
python3 -m pip install -r SpotiUtil/requirements.txt
```

### Step 3: Get Spotify API Credentials

This program uses the Spotify APi for most of its functionality. In order to do this,
you need to get API credentials from spotify. 

Navigate to the [Spotify Developer Portal](https://developer.spotify.com/) and 
log in to your Spotify account.

Click your username in the top-right corner, the select "Dashboard". After that 
select "Create App". 

Give the app a name and a description, set the 

### Step 4: Create Datafiles

This program uses a few datafiles to save user data. By default, the program 
will look in the `SpotiUtil/dataFiles` folder, you can change this location in 
`main.py`. Duplicate the `SpotiUtil/example dataFiles` folder and rename it 
to `datafiles`



 

