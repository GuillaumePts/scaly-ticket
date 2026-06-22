from toshiba_test32_exact_clone import draw_single_label, build_job_exact_clone, DATA
img = draw_single_label(DATA)
job = build_job_exact_clone(img)
with open('test32.prn', 'wb') as f:
    f.write(job)
