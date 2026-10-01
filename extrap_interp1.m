function yq = extrap_interp1(x, y, xq, varargin)
% EXTRAP_INTERP1  带线性外推的插值函数
%   支持：自动排序、去重、边界外推（用端点斜率）
%   用法：yq = extrap_interp1(x, y, xq)

    p = inputParser;
    addParameter(p, 'method', 'linear', @(s)any(validatestring(s,{'linear','spline','nearest','pchip'})));
    parse(p, varargin{:});
    method = p.Results.method;

    x = x(:);  xq = xq(:);
    [x, ia, ~] = unique(x, 'stable');
    y = y(ia, :);

    if numel(x) < 2
        yq = repmat(y, size(xq)); return;
    end

    % 端点斜率
    k_left  = (y(2) - y(1)) / (x(2) - x(1));
    k_right = (y(end) - y(end-1)) / (x(end) - x(end-1));

    yq = zeros(size(xq,1), size(y,2));

    % 左外推
    idxL = xq < x(1);
    yq(idxL,:) = y(1,:) + k_left .* (xq(idxL) - x(1));

    % 右外推
    idxR = xq > x(end);
    yq(idxR,:) = y(end,:) + k_right .* (xq(idxR) - x(end));

    % 中间插值
    idxM = ~(idxL | idxR);
    if any(idxM)
        yq(idxM,:) = interp1(x, y, xq(idxM), method);
    end
end