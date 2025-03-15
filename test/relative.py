#
# Test relative imports.
#

import liveimport
from setup import *

# globals() access means this can't be defined in setup
def is_registered(modulename:str, name:str|None=None, asname:str|None=None):
    return liveimport._is_registered(globals(),modulename,name,asname)


def test_relative_import_dependency():
    """
    Verify dependency analysis resolves relative imports.
    """
    liveimport.register(globals(),"""
    import mod1
    import pkg.smod1
    import pkg.subpkg.ssmod1
    import pkg.subpkg.ssmod2
    from mod3 import *
    """)

    touch_module("mod1")
    reload_clear()
    liveimport.sync(observer=reload_observe)
    reload_expect("mod1")

    touch_module("pkg.smod1")
    reload_clear()
    liveimport.sync(observer=reload_observe)
    reload_expect("pkg.smod1",
                  "pkg.subpkg.ssmod2",
                  "mod3")

    touch_module("pkg.subpkg.ssmod1")
    reload_clear()
    liveimport.sync(observer=reload_observe)
    reload_expect("pkg.subpkg.ssmod1",
                  "pkg.subpkg.ssmod2",
                  "mod3")


def test_bad_relative_import_dependency():
    """
    Dependency analysis should raise ModuleError with an ImportError cause for
    invalid relative imports.
    """
    liveimport.register(globals(),"""
    import mod1
    import pkg.smod1
    import pkg.subpkg.ssmod1
    import pkg.subpkg.ssmod2
    from mod3 import *
    """)

    with revised_module("pkg.subpkg.ssmod2",imports=[
        "from ... smod1 import tag as smod1_public1"]):
        try:
            liveimport.sync()
            error = None
        except liveimport.ModuleError as ex:
            error = ex
        
        assert error is not None
        assert isinstance(error.__cause__,ImportError)


def test_register_relative():
    """
    Verify register() resolves relative imports.
    """

    liveimport.register(globals(),"from . ssmod1 import ssmod1_public1",
                        package="pkg.subpkg")

    assert is_registered("pkg.subpkg.ssmod1")
    assert is_registered("pkg.subpkg.ssmod1","ssmod1_public1")

    liveimport.register(globals(),"from .. smod2 import smod2_public1",
                        package="pkg.subpkg")

    assert is_registered("pkg.smod2")
    assert is_registered("pkg.smod2","smod2_public1")


def test_register_bad_relative():
    """
    register() should raise ImportError for invalid relative imports.
    """
    try:
        liveimport.register(globals(),"from ... smod2 import smod2_public1",
                            package="pkg.subpkg")
        error = None
    except ImportError as ex:
        error = ex
    
    assert error is not None
