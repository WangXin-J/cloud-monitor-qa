package monitor;

/**
 * 告警规则的最小参考实现，只为了说明「单测该覆盖哪些边界」。
 *
 * 换成你自己项目里的 AlertRule 时，保留 evaluate(value, nowSeconds) 的语义即可，
 * 下面的测试用例可以几乎原样搬过去 —— 边界条件不随实现变。
 */
public class AlertRule {

    private final String metric;
    private final String operator;
    private final double threshold;
    private final int consecutive;
    private final int silenceSeconds;

    private int hitCount;
    private boolean fired = false;
    private long lastFiredAt = -1;

    public AlertRule(String metric, String operator, double threshold, int consecutive, int silenceSeconds) {
        if (consecutive < 1) {
            throw new IllegalArgumentException("consecutive 必须 >= 1");
        }
        if (silenceSeconds < 0) {
            throw new IllegalArgumentException("silenceSeconds 不能为负");
        }
        this.metric = metric;
        this.operator = operator;
        this.threshold = threshold;
        this.consecutive = consecutive;
        this.silenceSeconds = silenceSeconds;
    }

    /**
     * @return true 表示本次应该真正发出告警（已经过连续次数和冷却期的过滤）
     */
    public boolean evaluate(double value, long nowSeconds) {
        if (!matches(value)) {
            hitCount = 0;
            return false;
        }
        hitCount++;
        if (hitCount < consecutive) {
            return false;
        }
        if (fired && nowSeconds - lastFiredAt < silenceSeconds) {
            return false;
        }
        hitCount = 0;
        fired = true;
        lastFiredAt = nowSeconds;
        return true;
    }

    private boolean matches(double value) {
        switch (operator) {
            case ">":
                return value > threshold;
            case ">=":
                return value >= threshold;
            case "<":
                return value < threshold;
            case "<=":
                return value <= threshold;
            default:
                throw new IllegalStateException("未知 operator: " + operator);
        }
    }

    public String getMetric() {
        return metric;
    }

    public int getHitCount() {
        return hitCount;
    }
}
