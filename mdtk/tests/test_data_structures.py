import os
import pandas as pd
import numpy as np
from mdtk.data_structures import (
    Composition, Pianoroll, read_note_csv, fix_overlapping_notes,
    check_overlap, check_monophonic, check_overlapping_pitch, check_note_df,
    get_monophonic_tracks, make_monophonic, quantize_df,
    plot_from_df, show_gridlines, plot_matrix, note_df_to_pretty_midi,
    synthesize_from_quant_df, synthesize_from_note_df, NOTE_DF_SORT_ORDER
)


# Test note DataFrames ========================================================
# Two notes in the same track overlap and have the same pitch
note_df_overlapping_pitch = pd.DataFrame({
    'onset': [0, 1],
    'track' : 0,
    'pitch': [60, 60],
    'dur': [2, 1]
})
note_df_overlapping_pitch_fix = pd.DataFrame({
    'onset': [0, 1],
    'track' : 0,
    'pitch': [60, 60],
    'dur': [1, 1]
})
# Two notes in the same track overlap but have different pitches
note_df_overlapping_note = pd.DataFrame({
    'onset': [0, 1],
    'track' : 0,
    'pitch': [60, 61],
    'dur': [2, 1]
})
# Incorrect pitch sort order, polyphonic track 0
note_df_2pitch_aligned = pd.DataFrame({
    'onset': [0, 0, 1, 2, 3, 4],
    'track' : 0,
    'pitch': [61, 60, 60, 60, 60, 60],
    'dur': [4, 1, 1, 0.5, 0.5, 2]
})
# Not quantized, polyphonic
note_df_2pitch_weird_times = pd.DataFrame({
    'onset': [0, 0, 1.125, 1.370],
    'track' : 0,
    'pitch': [60, 61, 60, 60],
    'dur': [.9, 1.6, .24, 0.125]
})
# Expected quantization of the above at 12 divisions per integer
# N.B. Although the duration of .24 would quantize to 3, this would create
# an overlapping pitch, so it must be reduced to 2
note_df_2pitch_weird_times_quant = pd.DataFrame({
    'onset': [0, 0, 14, 16],
    'track' : 0,
    'pitch': [60, 61, 60, 60],
    'dur': [11, 19, 2, 2] 
})
# silence between 3.75 and 4
note_df_with_silence = pd.DataFrame({
    'onset': [0, 0, 1, 2, 3, 4],
    'track' :[0, 1, 0, 0, 0, 0],
    'pitch': [60, 61, 60, 60, 60, 60],
    'dur': [1, 3.75, 1, 0.5, 0.5, 2]
})
# midinote keyboard range from 0 to 127 inclusive
all_midinotes = list(range(0, 128))
# All pitches played simultaneously for 1 quantum
all_pitch_df_notrack = pd.DataFrame({
    'onset': [0] * len(all_midinotes),
    'pitch': all_midinotes,
    'dur': [1] * len(all_midinotes)
})
all_pitch_df = all_pitch_df_notrack.copy()
all_pitch_df['track'] = 1
all_pitch_df_wrongorder = all_pitch_df.copy()
all_pitch_df = all_pitch_df[NOTE_DF_SORT_ORDER]

nr_tracks = 3
track_names = np.random.choice(np.arange(10), replace=False, size=nr_tracks)
track_names.sort()
# All pitches played for duration 2 offset by 1 each, each track starting
# one onset after one another
all_pitch_df_tracks = pd.DataFrame({
    'onset': [x for sublist in [np.arange(ii, len(all_midinotes)*2 + ii, 2)
                                for ii in range(nr_tracks)]
              for x in sublist],
    'track': [x for sublist in [[name]*len(all_midinotes)
                                for name in track_names]
              for x in sublist],
    'pitch': all_midinotes * nr_tracks,
    'dur': [2] * (len(all_midinotes)*nr_tracks)
})
all_pitch_df_tracks_overlaps = pd.DataFrame({
    'onset': [x for sublist in [np.arange(ii, len(all_midinotes)*2 + ii, 2)
                                for ii in range(nr_tracks)]
              for x in sublist],
    'track': [x for sublist in [[name]*len(all_midinotes)
                                for name in track_names]
              for x in sublist],
    'pitch': all_midinotes * nr_tracks,
    'dur': [3] * (len(all_midinotes)*nr_tracks)
})
all_pitch_df_tracks_sparecol = all_pitch_df_tracks.copy(deep=True)
all_pitch_df_tracks_sparecol['sparecol'] = 'whoops'
df_all_mono = pd.DataFrame({
    'onset': [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
    'track' : [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
    'pitch': [60, 61, 62, 63, 70, 71, 72, 73, 80, 81, 82, 83],
    'dur': [1]*(4*3)
}).sort_values(by=NOTE_DF_SORT_ORDER).reset_index(drop=True)
df_some_mono = pd.DataFrame({
    'onset': [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
    'track' : [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
    'pitch': [60, 61, 62, 63, 70, 71, 72, 73, 80, 81, 82, 83],
    'dur': [1, 1, 1, 1, 4, 1, 1, 1, 1, 1, 1, 1]
}).sort_values(by=NOTE_DF_SORT_ORDER).reset_index(drop=True)
df_all_poly = pd.DataFrame({
    'onset': [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
    'track' : [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
    'pitch': [60, 61, 62, 63, 70, 71, 72, 73, 80, 81, 82, 83],
    'dur': [2, 1, 1, 1, 4, 1, 1, 1, 3, 1, 1, 1]
}).sort_values(by=NOTE_DF_SORT_ORDER).reset_index(drop=True)


ALL_DF = {
    'note_df_overlapping_pitch': note_df_overlapping_pitch,
    'note_df_overlapping_note': note_df_overlapping_note,
    'note_df_2pitch_aligned': note_df_2pitch_aligned,
    'note_df_2pitch_weird_times': note_df_2pitch_weird_times,
    'note_df_2pitch_weird_times_quant': note_df_2pitch_weird_times_quant,
    'note_df_with_silence': note_df_with_silence,
    'all_pitch_df_notrack': all_pitch_df_notrack,
    'all_pitch_df_wrongorder': all_pitch_df_wrongorder,
    'all_pitch_df': all_pitch_df,
    'all_pitch_df_tracks': all_pitch_df_tracks,
    'all_pitch_df_tracks_overlaps': all_pitch_df_tracks_overlaps,
    'all_pitch_df_tracks_sparecol': all_pitch_df_tracks_sparecol,
    'df_all_mono': df_all_mono,
    'df_some_mono': df_some_mono,
    'df_all_poly': df_all_poly
}

sort_err = (f"note_df must be sorted by {NOTE_DF_SORT_ORDER} and columns "
            "ordered")
missing_col_err = (f"note_df must contain all columns in {NOTE_DF_SORT_ORDER}")
col_order_err = (f"note_df colums must be in order: {NOTE_DF_SORT_ORDER}")
extra_col_err = (f"note_df must only contain columns in {NOTE_DF_SORT_ORDER}")
overlap_err = ('Track(s) {bad_tracks} has an overlapping note at pitch(es) '
               '{bad_pitches}, i.e. there is a note which overlaps another '
               'at the same pitch')
ASSERTION_ERRORS = {
    'note_df_overlapping_pitch': overlap_err.format(bad_tracks=[0],
                                                    bad_pitches=[60]),
    'note_df_overlapping_note': None,
    'note_df_2pitch_aligned': sort_err,
    'note_df_2pitch_weird_times': None,
    'note_df_2pitch_weird_times_quant': None,
    'note_df_with_silence': None,
    'all_pitch_df_notrack': missing_col_err,
    'all_pitch_df_wrongorder': col_order_err,
    'all_pitch_df': None,
    'all_pitch_df_tracks': sort_err,
    'all_pitch_df_tracks_overlaps': sort_err,
    'all_pitch_df_tracks_sparecol': extra_col_err,
    'df_all_mono': None,
    'df_some_mono': None,
    'df_all_poly': None
}

def fix_sort(df):
    return (
        df
            .sort_values(by=NOTE_DF_SORT_ORDER)
            .reset_index(drop=True)
    )[NOTE_DF_SORT_ORDER]
    
ALL_VALID_DF = {
    'note_df_overlapping_pitch': note_df_overlapping_pitch_fix,
    'note_df_overlapping_note': note_df_overlapping_note,
    'note_df_2pitch_aligned': fix_sort(note_df_2pitch_aligned),
    'note_df_2pitch_weird_times': note_df_2pitch_weird_times,
    'note_df_2pitch_weird_times_quant': note_df_2pitch_weird_times_quant,
    'note_df_with_silence': note_df_with_silence,
    'all_pitch_df_notrack': all_pitch_df,
    'all_pitch_df_wrongorder': all_pitch_df,
    'all_pitch_df': all_pitch_df,
    'all_pitch_df_tracks': fix_sort(all_pitch_df_tracks),
    'all_pitch_df_tracks_overlaps': fix_sort(all_pitch_df_tracks_overlaps),
    'all_pitch_df_tracks_sparecol': fix_sort(all_pitch_df_tracks_sparecol),
    'df_all_mono': df_all_mono,
    'df_some_mono': df_some_mono,
    'df_all_poly': df_all_poly
}


for name, df in ALL_DF.items():    
    df.to_csv(f'./{name}.csv', index=False)

all_pitch_df_tracks_sparecol.to_csv(
        './all_pitch_df_tracks_sparecol_noheader.csv',
        index=False,
        header=False
    )
weird_col_order = ['pitch','track','sparecol','dur','onset']
all_pitch_df_tracks_sparecol[weird_col_order].to_csv(
        './all_pitch_df_tracks_sparecol_weirdorder.csv',
        index=False
    )

ALL_CSV = [f'./{name}.csv' for name in ALL_DF.keys()]
ALL_CSV += ['./all_pitch_df_tracks_sparecol_noheader.csv',
            './all_pitch_df_tracks_sparecol_weirdorder.csv']



# Function tests ==============================================================
def test_read_note_csv():
    df = read_note_csv('./all_pitch_df.csv', track=None)
    assert not df.equals(all_pitch_df)  # track names don't match
    all_pitch_df_track_name_change = all_pitch_df.copy()
    all_pitch_df_track_name_change['track'] = 0
    assert df.equals(all_pitch_df_track_name_change)
    df = read_note_csv('./all_pitch_df.csv', track='track')
    assert df.equals(all_pitch_df)
    df = read_note_csv('./all_pitch_df_tracks.csv', track='track', sort=False)
    assert df.equals(all_pitch_df_tracks[NOTE_DF_SORT_ORDER]), (
            f"{df}\n\n\n{all_pitch_df_tracks[NOTE_DF_SORT_ORDER]}")
    df = read_note_csv('./all_pitch_df_tracks_sparecol.csv', track='track',
                       sort=False)
    comp_df = all_pitch_df_tracks_sparecol[NOTE_DF_SORT_ORDER + ['sparecol']]
    assert df.equals(comp_df.drop('sparecol', axis=1))
    df = read_note_csv('./all_pitch_df_tracks_sparecol.csv', track='track')
    assert not df.equals(comp_df.drop('sparecol', axis=1))  # sorting
    assert df.equals(
            (comp_df
                 .drop('sparecol', axis=1)
                 .sort_values(by=NOTE_DF_SORT_ORDER)
                 .reset_index(drop=True)
            )[NOTE_DF_SORT_ORDER])  # sorting
    df = read_note_csv('./all_pitch_df_tracks_sparecol_weirdorder.csv',
                       track='track', sort=False)
    assert df.equals(comp_df.drop('sparecol', axis=1))
    

def test_check_overlap():
    assert check_overlap(note_df_overlapping_pitch)
    assert check_overlap(note_df_overlapping_note)
    assert not check_overlap(note_df_overlapping_pitch_fix)
    

def test_check_overlapping_pitch():
    assert check_overlapping_pitch(note_df_overlapping_pitch)
    assert not check_overlapping_pitch(note_df_overlapping_pitch_fix)
    assert not check_overlapping_pitch(note_df_overlapping_note)


def test_check_note_df():
    for name, df in ALL_DF.items():
        err = ASSERTION_ERRORS[name]
        # If df will error, check it errors and the assertion correct
        if err is not None:
            correctly_errored = False
            try:
                check_note_df(df)
            except AssertionError as e:
                correctly_errored = True
                assert e.args == (err,), (f'{name} did error but the '
                    'assertion text was incorrect')
            assert correctly_errored, f'{name} did not error and it should'
        # Check the corrected version *does* pass
        assert check_note_df(ALL_VALID_DF[name]), (f'Fixed version of {name} '
            'should pass the tests but does not')


def test_check_monophonic():
    assert all(check_monophonic(df_all_mono))
    assert (check_monophonic(df_some_mono, raise_error=False) 
            == [True, False, True])
    assert (check_monophonic(df_all_poly, raise_error=False) 
            == [False, False, False])
    assert all(check_monophonic(all_pitch_df_tracks))
    correctly_errored = False
    try:
        check_monophonic(all_pitch_df_tracks_overlaps)
    except AssertionError as e:
        correctly_errored = True
        assert e.args == (f"Track(s) {list(track_names)} has a note with a "
                          "duration overlapping a subsequent note onset",)
    assert correctly_errored


def test_fix_overlapping_notes():
    assert note_df_overlapping_pitch_fix.equals(
            fix_overlapping_notes(note_df_overlapping_pitch.copy())
        )


def test_get_monophonic_tracks():
    assert get_monophonic_tracks(df_all_mono) == [0, 1, 2]
    assert get_monophonic_tracks(df_some_mono) == [0, 2]
    assert get_monophonic_tracks(df_all_poly) == []
    assert (get_monophonic_tracks(all_pitch_df_tracks)
            == list(track_names))
    assert get_monophonic_tracks(all_pitch_df_tracks_overlaps) == []


def test_make_monophonic():
    assert make_monophonic(df_all_poly).equals(df_all_mono)

def test_quantize_df():
    assert note_df_2pitch_weird_times_quant.equals(
            quantize_df(note_df_2pitch_weird_times, 12))


 # Pianoroll class tests ======================================================
def test_pianoroll_all_pitches():
    pianoroll = Pianoroll(quant_df=all_pitch_df)
    assert (pianoroll == np.ones((1, 2, 128, 1), dtype='uint8')).all()
    

# TODO: test all note_on occur with sounding
    
# TODO: test all note_off occur with sounding

# TODO: test all sounding begin note_on and end_note_off

# TODO: test all methods in pianoroll and all attributes


# Composition class tests =====================================================
# TODO: write import from csv tests    

def test_composition_df_assertions():
    """Essentially the same tests as test_check_note_df"""
    assertion = False
    try:
        Composition(note_df=all_pitch_df_notrack)
    except AssertionError as e:
        if e.args == ("note_df must contain all columns in ['onset', 'track', "
                      "'pitch', 'dur']",):
            assertion = True
    assert assertion
    assertion = False
    
    assertion = False
    try:
        Composition(note_df=note_df_2pitch_aligned)
    except AssertionError as e:
        if e.args == ("note_df must be sorted by ['onset', 'track', 'pitch', "
                      "'dur'] and columns ordered",):
            assertion = True
    assert assertion
    assertion = False
    
    try:
        Composition(
            note_df=note_df_2pitch_aligned.sort_values(NOTE_DF_SORT_ORDER)
        )
    except AssertionError as e:
        if e.args == ("note_df must have a RangeIndex with integer steps",):
            assertion = True
    assert assertion
    
    assert Composition(
            note_df=(
                note_df_2pitch_aligned
                    .sort_values(NOTE_DF_SORT_ORDER)
                    .reset_index(drop=True)
            )
        )


def test_composition_all_pitches():
    c = Composition(note_df=all_pitch_df, quantization=1)
    pr = np.ones_like(c.pianoroll)
    assert (pr == c.pianoroll).all()



# TODO: reimplement this if and when we implement auto fix of note_df
#def test_auto_sort_onset_and_pitch():
#    comp = Composition(note_df=note_df_2pitch_aligned, fix_note_df=True)
#    assert comp.note_df.equals(
#        note_df_2pitch_aligned
#            .sort_values(['onset', 'pitch'])
#            .reset_index(drop=True)
#    )


def test_not_ending_in_silence():
    for df in ALL_VALID_DF.values():
        comp = Composition(note_df=df)
        assert not (comp.pianoroll[:, 0, :, -1] == 0).all(), (f'{df}',
                   f'{comp.plot()} {comp.pianoroll}')


def test_nr_note_on_equals_nr_notes():
    for df in ALL_VALID_DF.values():
        comp = Composition(note_df=df)
        pianoroll = comp.pianoroll
        assert np.sum(pianoroll[:, 1, :, :]) == comp.note_df.shape[0]


def test_all_composition_methods_and_attributes():
    compositions = [Composition(comp)
                    for comp in ALL_VALID_DF.values()]
    for comp in compositions:
        comp.csv_path
        comp.note_df
        comp.quantization
        comp.quant_df
        comp.pianoroll
        comp.quanta_labels
        comp.plot()
        comp.synthesize()

# TODO: Check if anything alters input data - loop over all functions and
#       methods


# Cleanup =====================================================================
# TODO: This isn't technichally a test...should probably be some other function
#       look up the proper way to do this.
def test_remove_csvs(): 
    for csv in ALL_CSV:
        os.remove(csv)