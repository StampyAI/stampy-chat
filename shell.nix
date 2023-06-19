{ pkgs ? import <nixpkgs> {} }:
let
  python = pkgs.python311;
  pythonPackages = python.pkgs;
  python3Env = python.withPackages (ps: with ps; [
    numpy
    pylint
  ]);
in

with pkgs; mkShell {
  name = "pip-env";
  buildInputs = [
    pipenv
    python311
    (pkgs.callPackage ./web/default.nix {  }).shell
  ];

 # shellHook = ''
 #   # Allow the use of wheels.
 #   SOURCE_DATE_EPOCH=$(date +%s)

 #   # Augment the dynamic linker path or other packages you care about
 #   export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${pkgs.ncurses}/lib

 #   VENV=master37env
 #   if test ! -d $VENV; then
 #     virtualenv $VENV
 #   fi
 #   source ./$VENV/bin/activate

 #   # allow for the environment to pick up packages installed with virtualenv
 #   export PYTHONPATH=`pwd`/$VENV/${python.sitePackages}/:$PYTHONPATH
 # '';
}
