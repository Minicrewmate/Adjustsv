import os
import sys
import codecs
from collections import defaultdict

def parse_timing_points(lines):
    bpm_points = []
    sv_points = []
    for line in lines:
        if line.strip() == '' or line.startswith('//'):
            continue
        parts = line.strip().split(',')
        if len(parts) >= 8:
            offset = int(float(parts[0]))
            ms_per_beat = float(parts[1])
            uninherited = parts[6] == '1'
            if uninherited:
                bpm_points.append((offset, ms_per_beat))
            else:
                sv_points.append((offset, ms_per_beat))
    return bpm_points, sv_points

def find_dominant_bpm(bpm_points, song_end_time):
    durations = defaultdict(int)
    for i in range(len(bpm_points)):
        start = bpm_points[i][0]
        end = bpm_points[i + 1][0] if i + 1 < len(bpm_points) else song_end_time
        bpm = round(60000 / bpm_points[i][1], 6)
        durations[bpm] += end - start
    dominant_bpm = max(durations.items(), key=lambda x: x[1])[0]
    return dominant_bpm

def generate_sv_points(bpm_points, existing_sv_points, dominant_bpm):
    dominant_mpbeat = 60000 / dominant_bpm
    existing_sv_offsets = {offset for offset, _ in existing_sv_points}
    new_sv_points = []
    for offset, ms_per_beat in bpm_points:
        if offset not in existing_sv_offsets:
            sv = -dominant_mpbeat / ms_per_beat * 100
            new_sv_points.append((offset, sv))
    return sorted(existing_sv_points + new_sv_points)

def update_osu_file(filepath):
    with codecs.open(filepath, 'r', 'utf-8') as f:
        lines = f.readlines()

    timing_start = None
    for i, line in enumerate(lines):
        if line.strip() == '[TimingPoints]':
            timing_start = i + 1
            break

    if timing_start is None:
        print("[TimingPoints] セクションが見つかりません。")
        return

    timing_end = timing_start
    while timing_end < len(lines) and lines[timing_end].strip() != '':
        timing_end += 1

    timing_lines = lines[timing_start:timing_end]
    bpm_points, sv_points = parse_timing_points(timing_lines)

    # 曲の終了時刻を推定
    hitobject_start = None
    for i, line in enumerate(lines):
        if line.strip() == '[HitObjects]':
            hitobject_start = i + 1
            break

    song_end_time = 1000000
    if hitobject_start:
        hit_times = [int(ln.split(',')[2]) for ln in lines[hitobject_start:] if ln.strip() != '']
        if hit_times:
            song_end_time = max(hit_times) + 10000

    dominant_bpm = find_dominant_bpm(bpm_points, song_end_time)
    new_sv_points = generate_sv_points(bpm_points, sv_points, dominant_bpm)

    # bpmポイントだけ保持し、svは再構成する
    new_timing_lines = [f"{offset},{mpb},4,1,0,100,1,0\n" for offset, mpb in bpm_points]
    new_timing_lines += [f"{offset},{sv:.15f},4,1,0,100,0,0\n" for offset, sv in new_sv_points]

    new_lines = lines[:timing_start] + new_timing_lines + lines[timing_end:]

    new_path = filepath.replace('.osu', '_adjusted.osu')
    with codecs.open(new_path, 'w', 'utf-8') as f:
        f.writelines(new_lines)

    print(f"修正済みのファイルを出力しました: {new_path}")

if __name__ == '__main__':
    filepath = input("読み込む .osu ファイルのパスを入力してください: ").strip('"')
    if not os.path.isfile(filepath):
        print("ファイルが存在しません。")
        sys.exit(1)
    update_osu_file(filepath)