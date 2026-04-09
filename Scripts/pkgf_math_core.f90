module pkgf_math_core
    use iso_c_binding
    implicit none

    contains

    subroutine linear_fit(n, x, y, slope, intercept)
        integer, intent(in) :: n
        real(8), intent(in) :: x(n), y(n)
        real(8), intent(out) :: slope, intercept
        real(8) :: sum_x, sum_y, sum_xx, sum_xy, det
        sum_x = sum(x); sum_y = sum(y); sum_xx = dot_product(x, x); sum_xy = dot_product(x, y)
        det = dble(n) * sum_xx - sum_x**2
        if (abs(det) < 1.0d-12) then
            slope = 0.0d0; intercept = sum_y / dble(n)
        else
            slope = (dble(n) * sum_xy - sum_x * sum_y) / det
            intercept = (sum_xx * sum_y - sum_x * sum_xy) / det
        end if
    end subroutine linear_fit

    subroutine sort_int(n, a)
        integer, intent(in) :: n
        integer, intent(inout) :: a(n)
        integer :: i, j, tmp
        do i = 1, n-1
            do j = i+1, n
                if (a(i) > a(j)) then
                    tmp = a(i); a(i) = a(j); a(j) = tmp
                end if
            end do
        end do
    end subroutine sort_int

    subroutine compute_hurst(n, x, h_val) bind(c, name='compute_hurst')
        integer(c_int), value :: n
        real(c_double), intent(in) :: x(n)
        real(c_double), intent(out) :: h_val
        integer :: max_scale, n_scales, s, i, j, k, n_seg, rs_count, valid_segs
        integer, allocatable :: sizes(:)
        real(8), allocatable :: ns_log(:), RS_log(:), seg(:), z(:)
        real(8) :: seg_mean, seg_std, r, slope, intercept, rs_sum
        max_scale = int(floor(log(dble(n)) / log(2.0d0)))
        n_scales = max(0, max_scale - 3)
        if (n_scales < 2) then; h_val = 0.5d0; return; end if
        allocate(sizes(n_scales))
        do i = 1, n_scales; sizes(i) = 2**(i+2); end do
        allocate(ns_log(n_scales)); allocate(RS_log(n_scales)); rs_count = 0
        do i = 1, n_scales
            s = sizes(i); n_seg = n / s; rs_sum = 0.0d0; valid_segs = 0
            allocate(seg(s)); allocate(z(s))
            do j = 1, n_seg
                seg = x((j-1)*s+1 : j*s); seg_mean = sum(seg) / dble(s)
                seg_std = sqrt(max(1.0d-14, sum((seg - seg_mean)**2) / dble(s)))
                if (seg_std > 1.0d-12) then
                    z(1) = seg(1) - seg_mean
                    do k = 2, s; z(k) = z(k-1) + (seg(k) - seg_mean); end do
                    r = maxval(z) - minval(z); rs_sum = rs_sum + (r / seg_std); valid_segs = valid_segs + 1
                end if
            end do
            if (valid_segs > 0) then
                rs_count = rs_count + 1; RS_log(rs_count) = log(rs_sum / dble(valid_segs))
                ns_log(rs_count) = log(dble(s))
            end if
            deallocate(seg, z)
        end do
        if (rs_count < 2) then; h_val = 0.5d0
        else; call linear_fit(rs_count, ns_log(1:rs_count), RS_log(1:rs_count), slope, intercept)
              h_val = min(1.0d0, max(0.0d0, slope)); end if
        deallocate(sizes, ns_log, RS_log)
    end subroutine compute_hurst

    subroutine compute_fractal_dim(n, x, d_val) bind(c, name='compute_fractal_dim')
        integer(c_int), value :: n
        real(c_double), intent(in) :: x(n)
        real(c_double), intent(out) :: d_val
        integer, parameter :: max_s = 5
        integer :: scales(max_s) = [2, 4, 8, 16, 32]
        real(8) :: log_counts(max_s), log_sizes(max_s)
        real(8) :: min_x, ptp_x, slope, intercept
        integer :: i, j, s, count, actual_n
        integer, allocatable :: bins(:)
        min_x = minval(x); ptp_x = maxval(x) - min_x + 1.0d-8
        actual_n = 0; allocate(bins(n))
        do i = 1, max_s
            s = scales(i); if (s >= n) exit
            do j = 1, n; bins(j) = int(floor((x(j) - min_x) / ptp_x * dble(s))); end do
            call sort_int(n, bins)
            count = 1
            do j = 2, n; if (bins(j) /= bins(j-1)) count = count + 1; end do
            actual_n = actual_n + 1
            log_counts(actual_n) = log(dble(count))
            log_sizes(actual_n) = log(1.0d0 / dble(s))
        end do
        if (actual_n < 2) then; d_val = 1.0d0
        else; call linear_fit(actual_n, log_sizes(1:actual_n), log_counts(1:actual_n), slope, intercept)
              d_val = -slope; end if ! CORRECTED SIGN
        deallocate(bins)
    end subroutine compute_fractal_dim

    subroutine compute_fisher(n, x, bins, f_val) bind(c, name='compute_fisher')
        integer(c_int), value :: n, bins
        real(c_double), intent(in) :: x(n)
        real(c_double), intent(out) :: f_val
        real(8) :: min_x, max_x, dx, sum_i, p(bins), p_mid, dp
        integer :: i, b_idx
        min_x = minval(x); max_x = maxval(x); dx = (max_x - min_x) / dble(bins)
        p = 0.0d0
        do i = 1, n
            b_idx = min(bins, max(1, int((x(i) - min_x) / dx) + 1))
            p(b_idx) = p(b_idx) + 1.0d0
        end do
        p = p / (dble(n) * dx) + 1.0d-12; sum_i = 0.0d0
        do i = 1, bins - 1
            dp = (p(i+1) - p(i)) / dx; p_mid = (p(i+1) + p(i)) / 2.0d0
            sum_i = sum_i + (dp**2 / p_mid)
        end do
        f_val = log(1.0d0 + sum_i * dx)
    end subroutine compute_fisher

    subroutine compute_mf_dfa_fluct(n, s, q, y, f_val) bind(c, name='compute_mf_dfa_fluct')
        integer(c_int), value :: n, s
        real(c_double), value :: q
        real(c_double), intent(in) :: y(n)
        real(c_double), intent(out) :: f_val
        integer :: n_seg, i, j
        real(8), allocatable :: seg(:), x_idx(:), var_s(:)
        real(8) :: slope, intercept, var_val, sum_fq
        n_seg = n / s; allocate(var_s(n_seg)); allocate(seg(s)); allocate(x_idx(s))
        do j = 1, s; x_idx(j) = dble(j-1); end do
        do i = 1, n_seg
            seg = y((i-1)*s+1 : i*s); call linear_fit(s, x_idx, seg, slope, intercept)
            var_val = 0.0d0
            do j = 1, s; var_val = var_val + (seg(j) - (slope * x_idx(j) + intercept))**2; end do
            var_s(i) = max(var_val / dble(s), 1.0d-12)
        end do
        if (abs(q) < 1.0d-10) then; f_val = exp(0.5d0 * sum(log(var_s)) / dble(n_seg))
        else; sum_fq = 0.0d0; do i = 1, n_seg; sum_fq = sum_fq + var_s(i)**(q/2.0d0); end do
              f_val = (sum_fq / dble(n_seg))**(1.0d0/q); end if
        deallocate(var_s, seg, x_idx)
    end subroutine compute_mf_dfa_fluct

end module pkgf_math_core
