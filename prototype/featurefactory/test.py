import glob
import os
import pandas as pd

from pyrem.feature_families import *
from pyrem.wavelet_decomposition import decompose_signal
from pyrem.io import polygram_from_pkl
from pyrem.polygram import Polygram

from multiprocessing import Pool
import numpy as np





DATA_FILE_PATTERN= "/data/pyrem/Ellys/pkls/*.pkl"
# DATA_FILE_PATTERN= "/data/pyrem/Ellys/pkls/TelC_*.pkl"


#OUT_CSV = "/data/pyrem/Ellys/all_features_e5s_plus_raw.csv"
OUT_CSV = "/data/pyrem/Ellys/all_features_e5s_eeg_more_features_plus_raw.csv"
WINDOW_SIZE = 5
WINDOW_LAG = 1

N_PROCESSES = 4




def features_one_file(f):
    file_name = os.path.basename(f).split(".")[0]
    treatment, animal = file_name.split("_")
    pol = polygram_from_pkl(f)

    #eegs = decompose_signal(pol["EEG_parietal_cereb"], levels=[1,2,3,4,5,6])
    eegs = decompose_signal(pol["EEG_parietal_frontal"], levels=[1,2,3,4,5,6])
    emgs = decompose_signal(pol["EMG_REF"],[1,2,3, 4], keep_a=False)

    #
    pol2 = eegs.merge(pol["EEG_parietal_frontal"])
    pol2 = pol2.merge(emgs)
    pol2 = pol2.merge(pol["EMG_REF"])
    pol2 = pol2.merge(pol["vigilance_state"])

    ##normalise
    pol2 = pol2.map_signal_channels(lambda c : (c - np.mean(c))/ np.std(c))


    feature_factory = [
                        PowerFeatures(),
                        HjorthFeatures(),

                        # NonLinearFeatures(),
                        #
                        # # FIXME skip for now -> speed
                        EntropyFeatures(),
                        FractalFeatures(),
                        VigilState(),]

    all_rows = []
    print "processing " + f
    old_p = 0
    for t, w in pol2.iter_window(WINDOW_SIZE, WINDOW_LAG):
        dfs = []
        for c in w.channels:
            for ff in feature_factory:
                feature_vec = ff.make_vector(c)
                if not feature_vec is None:
                    dfs.append(feature_vec)

        p = int(100 * t/ pol2.duration.total_seconds())
        if p != old_p:
            print f, p, "%"
            old_p = p

        row = pd.concat(dfs, axis=1)
        row.index = [t]

        all_rows.append(row)
    tmp_df = pd.concat(all_rows)

    tmp_df["animal"] = animal
    tmp_df["treatment"] = treatment



    return tmp_df

if __name__ == "__main__":

    files = glob.glob(DATA_FILE_PATTERN)

    if N_PROCESSES > 1 :
        p = Pool(N_PROCESSES)
        dfs = p.map(features_one_file, sorted(files))
    else:

        dfs = map(features_one_file, sorted(files))

    out_df = pd.concat(dfs)


    out_df.to_csv(OUT_CSV, float_format="%e")


"""
library(ggplot2)
df <- read.csv("/tmp/out.csv")
dfm <- aggregate(log10_dt ~ is_original * name * n,df, mean)
ggplot(dfm,aes(y = log10_dt, x = n, color=name, shape=name,  linetype=is_original)) +
        geom_point(size=2) + geom_smooth(method="lm", fill=NA, size=1.5)
mod <- lm(log10_dt ~ is_original * name * n,df)
"""