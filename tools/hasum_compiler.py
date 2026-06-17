#!/usr/bin/env python3
import re, subprocess, sys
from pathlib import Path

TYPE_MAP={"Nat":"Int","Int":"Int","Float":"Double","Text":"String","Bool":"Bool","LinearAutoDestroy":"LinearAutoDestroy"}

def transpile(src:str)->str:
    out=["{-# LANGUAGE DeriveAnyClass #-}","{-# LANGUAGE DeriveGeneric #-}","module Main where","import GHC.Generics (Generic)","import Control.DeepSeq (NFData)","import Control.Parallel.Strategies (parMap, rdeepseq)","", "newtype LinearAutoDestroy a = LinearAutoDestroy a deriving (Show, Generic, NFData)","consume :: LinearAutoDestroy a -> ()","consume _ = ()",""]
    used_destroyed=set()
    lines=src.splitlines()
    for ln,l in enumerate(lines,1):
        s=l.strip()
        if not s or s.startswith("--"): out.append(l); continue
        if s.startswith("extern "):
            # gleam-like extern declaration (only signature; no codegen)
            continue
        if s.startswith("parallel "):
            m=re.match(r"parallel\s+([a-zA-Z_][\w]*)\s*\((.*?)\)\s*:\s*([\w]+)\s*=\s*(.*)",s)
            if not m: raise SystemExit(f"invalid parallel definition line {ln}")
            name,args,ret,expr=m.groups()
            hs_args=[]
            vars=[]
            if args.strip():
                for a in args.split(','):
                    an,at=[x.strip() for x in a.split(':')]
                    hs_args.append(f"{an} :: {TYPE_MAP.get(at,at)}")
                    vars.append(an)
            out.append(f"{name} :: {' -> '.join([TYPE_MAP.get(ret,ret)] if not hs_args else [h.split(' :: ')[1] for h in hs_args]+[TYPE_MAP.get(ret,ret)])}")
            out.append(f"{name} {' '.join(vars)} = {expr}")
            continue
        if s.startswith("benchmarkMap "):
            # benchmarkMap func listExpr
            _,fn,arr=s.split(maxsplit=2)
            out.append(f"benchmarkResult = parMap rdeepseq {fn} {arr}")
            continue
        if s.startswith("autodestroy "):
            # autodestroy var
            var=s.split()[1]
            used_destroyed.add(var)
            out.append(f"consume {var}")
            continue
        for v in list(used_destroyed):
            if re.search(rf"\b{re.escape(v)}\b", s):
                raise SystemExit(f"LinearAutoDestroy variable '{v}' referenced after destruction at line {ln}")
        out.append(l)
    out.append("main :: IO ()")
    out.append("main = pure ()")
    return "\n".join(out)+"\n"


def compile_file(path:Path):
    src=path.read_text()
    hs=path.with_suffix('.hs')
    hs.write_text(transpile(src))
    out=path.with_suffix('')
    cmd=["ghc","-threaded",str(hs),"-o",str(out)]
    print("[hasum]"," ".join(cmd))
    subprocess.run(cmd,check=True)

if __name__=='__main__':
    if len(sys.argv)<2: raise SystemExit("usage: hasum_compiler.py file.hasum [...]")
    for p in sys.argv[1:]:
        compile_file(Path(p))
