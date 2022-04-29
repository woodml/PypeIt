# -*- coding: utf-8 -*-
"""
Data utilities for built-in PypeIt data files

NOTE: If the hostname URL for the telluric atmospheric grids on S3 changes,
      the only place that needs to change is the file `s3_url.txt`.

.. include:: ../include/links.rst
"""
import os
import shutil
import urllib

import astropy.utils.data
import github
from linetools.spectra import xspectrum1d
from pkg_resources import resource_filename
import requests

from pypeit import io
from pypeit import msgs
from pypeit import __version__

__all__ = ['Paths', 'load_telluric_grid', 'load_thar_spec',
           'load_sky_spectrum', 'get_reid_arxiv_filepath',
           'get_skisim_filepath', 'get_spectrograph_gain_ronoise_dirpath',
           'get_sensfunc_filepath', 'fetch_remote_file', 'write_file_to_cache']


# Package-Data Paths =========================================================#
class Paths_meta(type):
    """MetaClass for Paths; only needed until python>=3.9

    The use of this metaclass is necessary until PypeIt sets python>=3.9, at
    which time, the methods shown below can be in the base Paths() class with
    the dual decorators:
        @classmethod
        @property

    This entire machinery is in place because we do not instantiate the Paths()
    class, but rather use it only as a container for the hardwired paths with
    error checking.

    TODO: Upon upgrade to python>=3.9, turn the metaclass into the Paths()
          class, and add the @classmethod decorator to each method.
    """
    def __init__(cls, *args, **kwargs):

        # Class Attributes -- Hardwired Paths
        cls._data = resource_filename('pypeit', 'data')

        # Telluric Corrections
        cls._telgrid = os.path.join(cls._data, 'telluric', 'atm_grids')
        cls._tel_model = os.path.join(cls._data, 'telluric', 'models')

        # Wavelength Calibrations
        cls._arclines = os.path.join(cls._data, 'arc_lines')
        cls._reid_arxiv = os.path.join(cls._data, 'arc_lines', 'reid_arxiv')
        cls._linelist = os.path.join(cls._data, 'arc_lines', 'lists')
        cls._nist = os.path.join(cls._data, 'arc_lines', 'NIST')
        cls._arc_plot = os.path.join(cls._data, 'arc_lines', 'plots')

        # Flux Calibrations
        cls._standards = os.path.join(cls._data, 'standards')
        cls._extinction = os.path.join(cls._data, 'extinction')
        cls._skisim = os.path.join(cls._data, 'skisim')
        cls._filters = os.path.join(cls._data, 'filters')
        cls._sensfuncs = os.path.join(cls._data, 'sensfuncs')

        # Other
        cls._sky_spec = os.path.join(cls._data, 'sky_spec')
        cls._static_calibs = os.path.join(cls._data, 'static_calibs')
        cls._spectrographs = os.path.join(cls._data, 'spectrographs')

    @property
    def data(cls):
        return check_isdir(cls._data)

    # Telluric Corrections
    @property
    def telgrid(cls):
        return check_isdir(cls._telgrid)
    @property
    def tel_model(cls):
        return check_isdir(cls._tel_model)

    # Wavelength Calibrations
    @property
    def arclines(cls):
        return check_isdir(cls._arclines)
    @property
    def reid_arxiv(cls):
        return check_isdir(cls._reid_arxiv)
    @property
    def linelist(cls):
        return check_isdir(cls._linelist)
    @property
    def nist(cls):
        return check_isdir(cls._nist)
    @property
    def arc_plot(cls):
        return check_isdir(cls._arc_plot)

    # Flux Calibrations
    @property
    def standards(cls):
        return check_isdir(cls._standards)
    @property
    def extinction(cls):
        return check_isdir(cls._extinction)
    @property
    def skisim(cls):
        return check_isdir(cls._skisim)
    @property
    def filters(cls):
        return check_isdir(cls._filters)
    @property
    def sensfuncs(cls):
        return check_isdir(cls._sensfuncs)

    # Other
    @property
    def sky_spec(cls):
        return check_isdir(cls._sky_spec)
    @property
    def static_calibs(cls):
        return check_isdir(cls._static_calibs)
    @property
    def spectrographs(cls):
        return check_isdir(cls._spectrographs)


class Paths(metaclass=Paths_meta):
    """List of hardwired paths within the pypeit.data module

    [extended_summary]
    """


# Remote-fetch functions for package data not distributed via PyPI ===========#
def get_reid_arxiv_filepath(arxiv_file):
    """Return the full path to the ``reid_arxiv`` file

    In an attempt to reduce the size of the PypeIt package as distributed on
    PyPI, the ``reid_arxiv`` files are not longer distributed with the package.
    The collection of files are hosted remotely, and only the ``reid_arxiv``
    files needed by a particular user are downloaded to the local machine.

    This function checks for the local existance of the ``reid_arxiv`` file, and
    downloads it from the remote server using AstroPy's ``download_file()``
    function.  The file downloaded in this fashion is kept in the PypeIt
    cache (nominally ``~/.pypeit/cache``) and is not placed into the package
    directory itself.

    The cache keeps a hash of the file URL, which contains the PypeIt version
    number.  As users update to newer versions, the ``reid_arxiv`` files will be
    downloaded again (matching the new version #) to catch any changes.

    As most users will need only a small number of ``reid_arxiv`` files for thier
    particular reductions, the remote fetch will only occur once per file (per
    version of PypeIt).

    Args:
        arxiv_file (str):
          The base filename of the ``reid_arxiv`` file to be located

    Returns:
        str: The full path to the ``reid_arxiv`` file
    """
    # Full path within the package data structure:
    reid_path = os.path.join(Paths.reid_arxiv, arxiv_file)

    # Check if the file does NOT exist in the package directory
    # NOTE: This should be the case for all but from-source installations
    if not os.path.isfile(reid_path):

        # Output an informational message
        msgs.info(f"reid_arxiv file {arxiv_file} does not exist in{msgs.newline()}"
                  "the package directory.  Checking cache or downloading the file now.")

        reid_path = fetch_remote_file(arxiv_file, "arc_lines/reid_arxiv")

    # Return the path to the `reid_arxiv` file
    return reid_path


def get_skisim_filepath(skisim_file):
    """Return the full path to the ``skisim`` file

    In an attempt to reduce the size of the PypeIt package as distributed on
    PyPI, the ``skisim`` files are not longer distributed with the package.
    The collection of files are hosted remotely, and only the ``skisim``
    files needed by a particular user are downloaded to the local machine.

    This function checks for the local existance of the ``skisim`` file, and
    downloads it from the remote server using AstroPy's ``download_file()``
    function.  The file downloaded in this fashion is kept in the PypeIt
    cache (nominally ``~/.pypeit/cache``) and is not placed into the package
    directory itself.

    The cache keeps a hash of the file URL, which contains the PypeIt version
    number.  As users update to newer versions, the ``skisim`` files will be
    downloaded again (matching the new version #) to catch any changes.

    As most users will need only a small number of ``skisim`` files for thier
    particular reductions, the remote fetch will only occur once per file (per
    version of PypeIt).

    Args:
        skisim_file (str):
          The base filename of the ``skisim`` file to be located

    Returns:
        str: The full path to the ``skisim`` file
    """
    # Full path within the package data structure:
    skisim_path = os.path.join(Paths.skisim, skisim_file)

    # Check if the file does NOT exist in the package directory
    # NOTE: This should be the case for all but from-source installations
    if not os.path.isfile(skisim_path):

        # Output an informational message
        msgs.info(f"skisim file {skisim_file} does not exist in{msgs.newline()}"
                  "the package directory.  Checking cache or downloading the file now.")

        skisim_path = fetch_remote_file(skisim_file, "skisim")

    # Return the path to the `skisim` file
    return skisim_path

def get_spectrograph_gain_ronoise_dirpath(spectrograph_name):
    """Return the full path to the ``data/spectrographs/gain_ronoise`` directory

    In an attempt to reduce the size of the PypeIt package as distributed on
    PyPI, the ``data/spectrograph/gain_ronoise`` directory is not longer distributed with the package.
    The collection of files are hosted remotely, and only the ``data/spectrographs/gain_ronoise``
    directory needed by a particular user are downloaded to the local machine.

    This function checks for the local existance of the ``data/spectrographs/gain_ronoise`` directory, and
    downloads it from the remote server using AstroPy's ``download_file()``
    function.  The file downloaded in this fashion is kept in the PypeIt
    cache (nominally ``~/.pypeit/cache``) and is not placed into the package
    directory itself.

    The cache keeps a hash of the file URL, which contains the PypeIt version
    number.  As users update to newer versions, the ``data/spectrographs/gain_ronoise`` directory will be
    downloaded again (matching the new version #) to catch any changes.

    As most users will need only a small number of ``data/spectrographs`` files for their
    particular reductions, the remote fetch will only occur once per file (per
    version of PypeIt).

    Args:
        spectrograph_name (str):
          Spectrograph name

    Returns:
        str: The full path to the ``data/spectrograph/gain_ronoise`` directory
    """
    # Full path within the package data structure:
    gain_ronoise_spectr_path = os.path.join(Paths.spectrographs, spectrograph_name, 'gain_ronoise')

    # Check if the directory does NOT exist in the package directory
    # NOTE: This should be the case for all but from-source installations
    if not os.path.isdir(gain_ronoise_spectr_path):

        # Output an informational message
        msgs.info(f"{spectrograph_name} gain_ronoise directory does not exist in{msgs.newline()}"
                  "the package directory.  Checking cache or downloading the file now.")

        gain_ronoise_spectr_path = fetch_remote_file(f'{spectrograph_name}/gain_ronoise', "spectrograph")

    # Return the path to the `gain_ronoise` directory
    return gain_ronoise_spectr_path


def get_sensfunc_filepath(sensfunc_file, symlink_in_pkgdir=False):
    """Return the full path to the ``sensfunc`` file

    In an attempt to reduce the size of the PypeIt package as distributed on
    PyPI, the ``sensfunc`` files are not longer distributed with the package.
    The collection of files are hosted remotely, and only the ``sensfunc``
    files needed by a particular user are downloaded to the local machine.

    This function checks for the local existance of the ``sensfunc`` file, and
    downloads it from the remote server using AstroPy's ``download_file()``
    function.  The file downloaded in this fashion is kept in the PypeIt
    cache (nominally ``~/.pypeit/cache``) and is not placed into the package
    directory itself.

    The cache keeps a hash of the file URL, which contains the PypeIt version
    number.  As users update to newer versions, the ``sensfunc`` files will be
    downloaded again (matching the new version #) to catch any changes.

    As most users will need only a small number of ``sensfunc`` files for thier
    particular reductions, the remote fetch will only occur once per file (per
    version of PypeIt).

    Args:
        sensfunc_file (str):
          The base filename of the ``sensfunc`` file to be located
        symlink_in_pkgdir (:obj:`bool`, optional):
          Create a symlink (with the canonical filename) in the package directory
          pointing to the cached downloaded file.  Defaults to False.

    Returns:
        str: The full path to the ``sensfunc`` file
    """
    # Full path within the package data structure:
    sensfunc_path = os.path.join(Paths.sensfuncs, sensfunc_file)

    # Check if the file does NOT exist in the package directory
    # NOTE: This should be the case for all but from-source installations
    if not os.path.isfile(sensfunc_path):

        # Output an informational message
        msgs.info(f"sensfunc file {sensfunc_file} does not exist in{msgs.newline()}"
                  "the package directory.  Checking cache or downloading the file now.")

        sensfunc_path = fetch_remote_file(sensfunc_file, "sensfuncs")

        # If requested, copy to package data directory and point the path there
        if symlink_in_pkgdir:
            path_in_pkgdir = os.path.join(Paths.sensfuncs, sensfunc_file)
            # Create the symlink
            os.symlink(sensfunc_path, path_in_pkgdir)
            # Return the path to the symlink in the package directory
            sensfunc_path = path_in_pkgdir

    # Return the path to the `sensfunc` file
    return sensfunc_path


def get_telgrid_filepath(telgrid_file):
    """Return the full path to the ``telgrid`` file

    Atmospheric Telluric Grid files are not part of the PypeIt package itself
    due to their large (~4-8GB) size.  These files are hosted remotely (see
    the PyepIt documentation), and only the ``telgrid`` files needed by a
    particular user are downloaded to the local machine.

    This function checks for the local existance of the ``telgrid`` file, and
    downloads it from the remote server using AstroPy's ``download_file()``
    function.  The file downloaded in this fashion is kept in the PypeIt
    cache (nominally ``~/.pypeit/cache``) and is not placed into the package
    directory itself.

    As most users will need only a small number of ``telgrid`` files for thier
    particular reductions, the remote fetch will only occur once per file.

    Args:
        sensfunc_file (str):
          The base filename of the ``sensfunc`` file to be located

    Returns:
        str: The full path to the ``sensfunc`` file
    """
    # Full path within the package data structure:
    telgrid_path = os.path.join(Paths.telgrid, telgrid_file)

    # Check if the file does NOT exist in the package directory
    # NOTE: This should be the case for most installations
    if not os.path.isfile(telgrid_path):

        # Output a brief warning for now -- makes it easier to find in the output
        msgs.info(f"telgrid file {telgrid_file} does not exist in{msgs.newline()}"
                  "the package directory.  Checking cache or downloading the file now.")

        telgrid_path = fetch_remote_file(telgrid_file, 'telluric/atm_grids', remote_host='s3_cloud')

        # If a development version, MOVE into the package directory, point path there
        if ".dev" in __version__:
            shutil.move(telgrid_path, os.path.join(Paths.telgrid, telgrid_file))
            telgrid_path = os.path.join(Paths.telgrid, telgrid_file)

    # Return the path to the `telgrid` file
    return telgrid_path


def fetch_remote_file(filename, filetype, remote_host='github', install_script=False,
                      force_update=False, full_url=None):
    """Use ``astropy.utils.data`` to fetch file from remote or cache

    The function ``download_file()`` will first look in the local cache (the option
    ``cache=True`` is used with this function to retrieve downloaded files from
    the cache, as needed) before downloading the file from the remote server.

    The remote file can be forcibly downloaded through the use of ``force_update``.

    Args:
        filename (str):
          The base filename to search for
        filetype (str):
          The subdirectory of ``pypeit/data/`` in which to find the file
          (e.g., ``arc_lines/reid_arxiv`` or ``sensfuncs``)
        remote_host (:obj:`str`, optional):
          The remote host scheme.  Currently only 'github' and 's3_cloud' are
          supported.  Defaults to 'github'].
        install_script (:obj:`bool`, optional):
          This function is being called from an install script (i.e.,
          ``pypeit_install_telluric``) -- relates to warnings displayed.
          Defaults to False.
        force_update (:obj:`bool`, optional):
          Force ``astropy.utils.data.download_file()`` to update the cache by
          downloading the latest version.  Defaults to False.
        full_url (:obj:`str`, optional):
          The full url (i.e., skip _build_remote_url())  Defaults to None.

    Returns:
        str: The local path to the desired file in the cache
    """
    # In some cases, we have the full URL already, but most of the time not
    if full_url:
        remote_url, sources = full_url, None
    else:
        remote_url, sources = _build_remote_url(filename, filetype, remote_host=remote_host)

    if remote_host == "s3_cloud" and not install_script:
        # Display a warning that this may take a while, and the user
        #   may wish to download using the `pypeit_install_telluric` script
        msgs.warn(f"You may wish to download {filename}{msgs.newline()}"
                    f"independently from your reduction by using the{msgs.newline()}"
                    "`pypeit_install_telluric` script.")

    # Get the file from cache, if available, or download from the remote server
    try:
        return astropy.utils.data.download_file(remote_url, cache="update" if force_update else True,
                                          sources=sources, timeout=10, pkgname="pypeit")

    except urllib.error.URLError as error:
        if remote_host == "s3_cloud" and (requests.head(sources[0]).status_code in
                                         [requests.codes.forbidden, requests.codes.not_found]):

            err_msg = (
                f"The file {filename}{msgs.newline()}"
                f"is not hosted in the cloud.  Please download this file from{msgs.newline()}"
                f"the PypeIt Google Drive and install it using the script{msgs.newline()}"
                f"pypeit_install_telluric --local.  See instructions at{msgs.newline()}"
                "https://pypeit.readthedocs.io/en/latest/installing.html#additional-data"
            )

        else:
            err_msg = (
                f"Error downloading {filename}: {error}{msgs.newline()}"
                f"URL attempted: {remote_url}{msgs.newline()}"
                f"If the error relates to the server not being found,{msgs.newline()}"
                f"check your internet connection.  If the remote server{msgs.newline()}"
                f"name has changed, please contact the PypeIt development{msgs.newline()}"
                "team."
            )

        # Raise the appropriate error message
        msgs.error(err_msg)


def write_file_to_cache(filename, cachename, filetype, remote_host="github"):
    """Use ``astropy.utils.data`` to save local file to cache

    This function writes a local file to the PypeIt cache as if it came from a
    remote server.  This is useful for being able to use locally created or
    separately downloaded files in place of PypeIt-distributed versions.

    Args:
        filename (str):
          The filename of the local file to save
        cachename (str):
          The name of the cached version of the file
        filetype (str):
          The subdirectory of ``pypeit/data/`` in which to find the file
          (e.g., ``arc_lines/reid_arxiv`` or ``sensfuncs``)
        remote_host (:obj:`str`, optional):
          The remote host scheme.  Currently only 'github' and 's3_cloud' are
          supported.  Defaults to 'github'.
    """
   # Build the `url_key` as if this file were in the remote location
    url_key, _ = _build_remote_url(cachename, filetype, remote_host=remote_host)

    # Use `import file_to_cache()` to place the `filename` into the cache
    astropy.utils.data.import_file_to_cache(url_key, filename, pkgname="pypeit")


def _build_remote_url(f_name, f_type, remote_host=""):
    """Build the remote URL for the ``astropy.utils.data`` functions

    This function keeps the URL-creation in one place.  In the event that files
    are moved from GitHub or S3_Cloud, this is the only place that would need
    to be changed.

    Args:
        f_name (str):
          The base filename to search for
        f_type (str):
          The subdirectory of ``pypeit/data/`` in which to find the file
          (e.g., ``arc_lines/reid_arxiv`` or ``sensfuncs``)
        remote_host (:obj:`str`, optional):
          The remote host scheme.  Currently only 'github' and 's3_cloud' are
          supported.  Defaults to ''.

    Returns:
        tuple: URLs for both cache storage name and current download link:

           * url (str): The URL of the ``f_name`` of ``f_type`` on server ``remote_host``
           * sources (:obj:`list` or :obj:`None`): For 's3_cloud', the list of URLs to
                actually try, passed to ``download_file()``, used in the event that the
                S3 location changes.  We maintain the static URL for the name to prevent
                re-downloading of large data files in the event the S3 location changes
                (but the file itself is unchanged).  If None (e.g. for 'github'), then
                ``download_file()`` is unaffected, and the ``url`` (above) is what
                controls the download.
    """
    if remote_host == "github":
        # Hard-wire the URL based on PypeIt Version
        data_url = (
            "https://raw.githubusercontent.com/pypeit/PypeIt/"
            f"{'develop' if '.dev' in __version__ else __version__}/pypeit/data/"
        )
        return f"{data_url}/{f_type}/{f_name}", None

    if remote_host == "s3_cloud":
        # Build up the (permanent, fake) `remote_url` and (fluid, real) `sources` for S3 Cloud
        return (f"https://s3.cloud.com/pypeit/{f_type}/{f_name}",
               [f"https://{_get_s3_hostname()}/pypeit/{f_type}/{f_name}"])

    msgs.error(f"Remote host type {remote_host} is not supported for package data caching.")


def _get_s3_hostname():
    """Get the current S3 hostname from the package file

    Since the S3 server hostname used to hold package data such as telluric
    atmospheric grids may change periodically, we keep the current hostname
    in a separate file (s3_url.txt), and pull the current version from the
    PypeIt ``release`` branch whenever needed.

    NOTE: When/if the S3 URL changes, the ``release`` branch version of
          ``s3_url.txt`` can be updated easily with a hotfix PR, and this
          routine will pull it.

    If GitHub cannot be reached, the routine uses the version of ``s3_url.txt``
    included with the package distribution.

    Returns:
        str: The current hostname URL of the S3 server holding package data
    """
    # Try getting the latest version from the server, else use what's included
    try:
        remote_url = (
            github.Github()
            .get_repo("pypeit/PypeIt")
            .get_contents("pypeit/data/s3_url.txt", "release")
            .download_url
        )
        filepath = astropy.utils.data.download_file(
            remote_url, cache="update", timeout=10, pkgname="pypeit"
        )
    except (urllib.error.URLError, github.GithubException):
        filepath = os.path.join(Paths.data, "s3_url.txt")

    # Open the file and return the URL
    with open(filepath, "r", encoding="utf-8") as fileobj:
        return fileobj.read().strip()


# Loading Functions for Particular File Types ================================#
def load_telluric_grid(filename):
    """Load a telluric atmospheric grid

    NOTE: This is where the path to the data directory is added!

    Args:
        filename (str):
          The filename (NO PATH) of the telluric atmospheric grid to use.

    Returns:
        (:obj:`astropy.io.fits.HDUList`): Telluric Grid FITS HDU list
    """
    # Check for existance of file parameter
    if not filename:
        msgs.error("No file specified for telluric correction.  "
                   "See https://pypeit.readthedocs.io/en/latest/telluric.html")

    # Get the data path for the filename, whether in the package directory or cache
    file_with_path = get_telgrid_filepath(filename)

    # Check for existance of file
    # NOTE: With the use of `get_telgrid_filepath()`, this should never run
    if not os.path.isfile(file_with_path):
        msgs.error(f"File {file_with_path} is not on your disk.  "
                   "You likely need to download the Telluric files.  "
                   "See https://pypeit.readthedocs.io/en/release/installing.html"
                   "#atmospheric-model-grids")

    return io.fits_open(file_with_path)


def load_thar_spec():
    """Load the archived ThAr spectrum

    NOTE: This is where the path to the data directory is added!

    Args:
        filename (str):
          The filename (NO PATH) of the telluric atmospheric grid to use.

    Returns:
        (:obj:`astropy.io.fits.HDUList`): ThAr Spectrum FITS HDU list
    """
    return io.fits_open(os.path.join(Paths.arclines, 'thar_spec_MM201006.fits'))


def load_sky_spectrum(sky_file):
    """Load a sky spectrum into an XSpectrum1D object

    NOTE: This is where the path to the data directory is added!

    .. todo::

        Try to eliminate the XSpectrum1D dependancy

    Args:
        sky_file (str):
          The filename (NO PATH) of the sky file to use.

    Returns:
        (:obj:`XSpectrum1D`): Sky spectrum
    """
    return xspectrum1d.XSpectrum1D.from_file(os.path.join(Paths.sky_spec, sky_file))


# Utility Function ===========================================================#
def check_isdir(path):
    """Check that the hardwired directory exists

    If yes, return the directory path, else raise NotADirectoryError
    """
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Unable to find {path}.  "
                                    "Check your installation.")
    return path
