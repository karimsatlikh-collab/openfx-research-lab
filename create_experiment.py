"""Create a versioned OpenFX experiment manifest without executing it."""
import argparse
import json

from openfx.experiment import new_experiment, save_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, dest="experiment_id")
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--strategy-version", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--start", required=True, dest="data_start")
    parser.add_argument("--end", required=True, dest="data_end")
    parser.add_argument("--parameters-json", default="{}")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    parameters = json.loads(args.parameters_json)
    if not isinstance(parameters, dict):
        parser.error("--parameters-json must decode to a JSON object")
    manifest = new_experiment(
        experiment_id=args.experiment_id,
        hypothesis=args.hypothesis,
        strategy_version=args.strategy_version,
        symbol=args.symbol,
        timeframe=args.timeframe,
        data_start=args.data_start,
        data_end=args.data_end,
        parameters=parameters,
    )
    save_manifest(manifest, args.output)
    print(json.dumps({"created": args.output, "status": manifest["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
